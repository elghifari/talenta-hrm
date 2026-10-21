import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from employees.models import Employee

pytestmark = pytest.mark.django_db


@pytest.fixture
def hr(django_user_model):
    user = django_user_model.objects.create_user(email="import-hr@example.test")
    user.groups.add(Group.objects.get_or_create(name="HR")[0])
    client = Client()
    client.force_login(user)
    return client, user


def upload(client, content):
    data = content.encode("utf-8") if isinstance(content, str) else content
    return client.post(
        "/api/employees/import-preview/",
        {"file": SimpleUploadedFile("employees.csv", data, content_type="text/csv")},
    )


def mixed_csv():
    return (
        "\ufeff Jabatan , ID Karyawan ,Nama Lengkap,Level,Tanggal Lahir,"
        "Tanggal Masuk,Kontrak Berakhir\r\n"
        'Terapis Senior,0001,"Karyawan A, Contoh",Level 2,1996-04-12,2024-01-01,2027-12-31\r\n'
        "Administrasi,0002,Karyawan Baru,Level 1,1998-03-21,2026-11-01,2027-10-31\r\n"
        "Terapis,0003,Karyawan Tetap,Level 1,1994-03-18,2022-07-01,2027-06-30\r\n"
    )


@pytest.fixture
def existing():
    first = Employee.objects.create(
        employee_code="0001",
        full_name="Karyawan A, Contoh",
        job_title="Terapis",
        level="Level 1",
        date_of_birth="1996-04-12",
        start_date="2024-01-01",
        contract_expiry="2026-12-31",
    )
    Employee.objects.create(
        employee_code="0003",
        full_name="Karyawan Tetap",
        job_title="Terapis",
        level="Level 1",
        date_of_birth="1994-03-18",
        start_date="2022-07-01",
        contract_expiry="2027-06-30",
    )
    Employee.objects.create(employee_code="9999", full_name="Outside CSV")
    return first


def test_preview_maps_reordered_headers_without_employee_writes(hr, existing):
    client, _ = hr
    response = upload(client, mixed_csv())
    assert response.status_code == 201
    body = response.json()
    assert [row["employee_code"] for row in body["rows"]] == ["0001", "0002", "0003"]
    assert [row["status"] for row in body["rows"]] == ["update", "new", "unchanged"]
    assert body["summary"] == {"new": 1, "update": 1, "unchanged": 1, "error": 0}
    assert set(body["rows"][0]["changes"]) == {"job_title", "level", "contract_expiry"}
    assert Employee.objects.count() == 3
    existing.refresh_from_db()
    assert existing.job_title == "Terapis" and existing.level == "Level 1"
    assert not AuditEvent.objects.exists()
    reload = client.get(f"/api/employees/imports/{body['id']}/")
    assert reload.status_code == 200
    assert reload.json()["rows"] == body["rows"]


def test_confirm_is_atomic_audited_and_idempotent(hr, existing):
    from employees.models import EmployeeImportBatch

    client, user = hr
    draft = upload(client, mixed_csv()).json()
    endpoint = f"/api/employees/imports/{draft['id']}/confirm/"
    first = client.post(endpoint, {}, content_type="application/json")
    assert first.status_code == 200
    assert first.json()["state"] == "committed"
    assert first.json()["summary"] == {"new": 1, "update": 1, "unchanged": 1, "error": 0}
    existing.refresh_from_db()
    assert existing.job_title == "Terapis Senior" and existing.level == "Level 2"
    assert str(existing.contract_expiry) == "2027-12-31"
    assert Employee.objects.get(employee_code="0002").date_of_birth.isoformat() == "1998-03-21"
    assert Employee.objects.count() == 4
    events = list(AuditEvent.objects.order_by("action").values_list("action", "actor_id"))
    assert events == [("employee.created", user.pk), ("employee.updated", user.pk)]
    second = client.post(endpoint, {}, content_type="application/json")
    assert second.status_code == 200 and second.json() == first.json()
    assert AuditEvent.objects.count() == 2
    assert client.get(f"/api/employees/imports/{draft['id']}/").json() == first.json()
    assert EmployeeImportBatch.objects.get(pk=draft["id"]).rows == []
