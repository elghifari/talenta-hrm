from datetime import timedelta

import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client
from django.utils import timezone
from employees.models import Employee, EmployeeImportBatch
from test_employee_import import existing as existing
from test_employee_import import hr as hr
from test_employee_import import mixed_csv, upload

pytestmark = pytest.mark.django_db


def confirm(client, draft, data=None):
    return client.post(
        f"/api/employees/imports/{draft['id']}/confirm/",
        {} if data is None else data,
        content_type="application/json",
    )


@pytest.mark.parametrize(
    "content",
    [
        "ID Karyawan,Nama Lengkap,Salary\n0001,Contoh,99\n",
        "ID Karyawan,ID Karyawan,Nama Lengkap\n0001,0001,Contoh\n",
        "ID Karyawan;Nama Lengkap\n0001;Contoh\n",
        'ID Karyawan,Nama Lengkap\n0001,"Unclosed\n',
        "ID Karyawan,Nama Lengkap\n0001\n",
        "ID Karyawan,Nama Lengkap\n",
        b"\xff\xfeINVALID",
        b"x" * (1024 * 1024 + 1),
        "ID Karyawan,Nama Lengkap\n" + "\n".join(f"{n:04},Contoh" for n in range(501)),
    ],
    ids=[
        "unknown",
        "duplicate-header",
        "semicolon",
        "quote",
        "short-row",
        "empty",
        "encoding",
        "size",
        "row-limit",
    ],
)
def test_bad_csv_is_rejected_without_draft_or_employee_writes(hr, content):
    client, _ = hr
    assert upload(client, content).status_code == 400
    assert not EmployeeImportBatch.objects.exists()
    assert not Employee.objects.exists() and not AuditEvent.objects.exists()


def test_bad_rows_remain_visible_and_block_entire_batch(hr):
    client, _ = hr
    body = upload(
        client,
        "ID Karyawan,Nama Lengkap,Tanggal Lahir\n"
        "0001,Valid,1996-01-01\n0002,,2999-01-01\n0003,A,\n0003,B,\n",
    ).json()
    assert [r["status"] for r in body["rows"]] == ["new", "error", "error", "error"]
    assert body["rows"][1]["errors"].keys() >= {"full_name", "date_of_birth"}
    assert confirm(client, body).status_code == 400
    assert not Employee.objects.exists() and not AuditEvent.objects.exists()


def test_missing_optional_columns_and_blank_cells_preserve_existing_data(hr, existing):
    client, _ = hr
    first = upload(client, 'ID Karyawan,Nama Lengkap\n0001,"Karyawan A, Contoh"\n').json()
    assert first["rows"][0]["status"] == "unchanged"
    second = upload(
        client,
        "Nama Lengkap,ID Karyawan,TTL,Jabatan,Level,Tanggal Masuk,Kontrak Berakhir\n"
        '"Karyawan A, Contoh",0001,,,,,\n',
    ).json()
    assert second["rows"][0]["status"] == "unchanged"
    assert confirm(client, second).status_code == 200
    existing.refresh_from_db()
    assert existing.job_title == "Terapis" and str(existing.date_of_birth) == "1996-04-12"
    assert not AuditEvent.objects.exists()


def test_canonical_dates_do_not_create_false_changes(hr, existing):
    client, _ = hr
    body = upload(
        client, 'ID Karyawan,Nama Lengkap,TTL\n0001,"Karyawan A, Contoh",1996-4-12\n'
    ).json()
    assert body["rows"][0]["incoming"]["date_of_birth"] == "1996-04-12"
    assert body["rows"][0]["status"] == "unchanged"


@pytest.mark.parametrize("change", ["update", "new-code", "delete"])
def test_changes_after_preview_reject_without_partial_writes(hr, existing, change):
    client, _ = hr
    draft = upload(client, mixed_csv()).json()
    if change == "update":
        Employee.objects.filter(pk=existing.pk).update(level="Concurrent Level")
    elif change == "new-code":
        Employee.objects.create(employee_code="0002", full_name="Concurrent Create")
    else:
        existing.delete()
    before = list(Employee.objects.values())
    assert confirm(client, draft).status_code == 409
    assert list(Employee.objects.values()) == before
    assert not AuditEvent.objects.exists()
    assert EmployeeImportBatch.objects.get(pk=draft["id"]).result is None


def test_draft_is_bound_to_owner_and_login_session(hr, django_user_model):
    client, user = hr
    draft = upload(client, "ID Karyawan,Nama Lengkap\n0001,Contoh\n").json()
    other = django_user_model.objects.create_user(email="other-import@example.test")
    other.groups.add(Group.objects.get(name="HR"))
    for account in (other, user):
        stranger = Client()
        stranger.force_login(account)
        response = stranger.get(f"/api/employees/imports/{draft['id']}/")
        assert response.status_code == 404
        assert confirm(stranger, draft).status_code == 404
        assert "Contoh" not in response.content.decode()
    assert not Employee.objects.exists() and not AuditEvent.objects.exists()


@pytest.mark.parametrize("role", ["KEPALA_UNIT", "FINANCE", "TECHNICAL_ADMIN", "INTERN", None])
def test_direct_restricted_requests_with_valid_csrf_are_denied(hr, django_user_model, role):
    client, _ = hr
    draft = upload(client, "ID Karyawan,Nama Lengkap\n0001,Contoh\n").json()
    user = django_user_model.objects.create_user(
        email="restricted-import@example.test", is_superuser=role is None
    )
    if role:
        user.groups.add(Group.objects.get_or_create(name=role)[0])
    restricted = Client(enforce_csrf_checks=True)
    restricted.force_login(user)
    token = restricted.get("/api/auth/csrf/").json()["csrfToken"]
    from django.core.files.uploadedfile import SimpleUploadedFile

    assert (
        restricted.post(
            "/api/employees/import-preview/",
            {"file": SimpleUploadedFile("a.csv", b"ID Karyawan,Nama Lengkap\n0001,Contoh\n")},
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 403
    )
    assert restricted.get(f"/api/employees/imports/{draft['id']}/").status_code == 403
    assert (
        restricted.post(
            f"/api/employees/imports/{draft['id']}/confirm/",
            {},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 403
    )
    assert not Employee.objects.exists() and not AuditEvent.objects.exists()


def test_role_revocation_and_expiry_block_draft(hr):
    client, user = hr
    draft = upload(client, "ID Karyawan,Nama Lengkap\n0001,Contoh\n").json()
    user.groups.clear()
    assert confirm(client, draft).status_code == 403
    user.groups.add(Group.objects.get(name="HR"))
    EmployeeImportBatch.objects.filter(pk=draft["id"]).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert client.get(f"/api/employees/imports/{draft['id']}/").status_code == 410
    assert confirm(client, draft).status_code == 410
    assert not Employee.objects.exists() and not AuditEvent.objects.exists()


def test_commit_rejects_client_supplied_changes(hr):
    client, _ = hr
    draft = upload(client, "ID Karyawan,Nama Lengkap\n0001,Contoh\n").json()
    assert confirm(client, draft, {"rows": [{"full_name": "Tampered"}]}).status_code == 400
    assert not Employee.objects.exists()


def test_hr_template_download_has_indonesian_headers(hr):
    client, _ = hr
    response = client.get("/api/employees/import-template/")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert (
        response.content.decode("utf-8-sig").splitlines()[0]
        == "ID Karyawan,Nama Lengkap,Cabang,Divisi,Tanggal Lahir,"
        "Jabatan,Level,Tanggal Masuk,Kontrak Berakhir"
    )


def test_pruning_removes_expired_pii_and_old_receipts(hr):
    client, _ = hr
    expired = upload(client, "ID Karyawan,Nama Lengkap\n0001,Expired\n").json()
    EmployeeImportBatch.objects.filter(pk=expired["id"]).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    receipt = upload(client, "ID Karyawan,Nama Lengkap\n0002,Committed\n").json()
    assert confirm(client, receipt).status_code == 200
    EmployeeImportBatch.objects.filter(pk=receipt["id"]).update(
        committed_at=timezone.now() - timedelta(days=2)
    )
    call_command("prune_employee_imports")
    assert not EmployeeImportBatch.objects.exists()
    assert Employee.objects.get(employee_code="0002").full_name == "Committed"
    assert AuditEvent.objects.count() == 1
