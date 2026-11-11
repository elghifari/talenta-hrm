import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from employees.models import Employee, EmployeeImportBatch

pytestmark = pytest.mark.django_db


@pytest.fixture
def hr_client(django_user_model):
    user = django_user_model.objects.create_user(email="permanent-expiry@example.test")
    user.groups.add(Group.objects.get_or_create(name="HR")[0])
    client = Client()
    client.force_login(user)
    return client


def test_permanent_create_rejects_contract_expiry_without_writes(hr_client):
    response = hr_client.post(
        "/api/employees/",
        {
            "employee_code": "PERM-01",
            "full_name": "Synthetic Permanent Employee",
            "employment_status": "permanen",
            "contract_expiry": "2027-12-31",
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "contract_expiry" in response.json()
    assert not Employee.objects.exists()
    assert not AuditEvent.objects.exists()


@pytest.mark.parametrize("expiry", [None, "2027-12-31"])
def test_permanent_patch_validates_expiry_against_stored_status(hr_client, expiry):
    employee = Employee.objects.create(
        employee_code="PERM-01", full_name="Synthetic Employee", employment_status="permanen"
    )
    response = hr_client.patch(
        f"/api/employees/{employee.pk}/",
        {"contract_expiry": expiry},
        content_type="application/json",
    )
    assert response.status_code == (200 if expiry is None else 400)
    employee.refresh_from_db()
    assert employee.contract_expiry is None
    assert AuditEvent.objects.count() == (1 if expiry is None else 0)


@pytest.mark.parametrize("explicit_clear", [False, True])
def test_becoming_permanent_requires_explicit_expiry_clear(hr_client, explicit_clear):
    employee = Employee.objects.create(
        employee_code="PERM-01",
        full_name="Synthetic Employee",
        employment_status="kontrak",
        pkwt_type="guru",
        contract_expiry="2027-12-31",
    )
    data = {"employment_status": "permanen"}
    if explicit_clear:
        data["contract_expiry"] = None
    response = hr_client.patch(
        f"/api/employees/{employee.pk}/", data, content_type="application/json"
    )
    assert response.status_code == (200 if explicit_clear else 400)
    employee.refresh_from_db()
    assert employee.employment_status == ("permanen" if explicit_clear else "kontrak")
    assert employee.pkwt_type == ("" if explicit_clear else "guru")
    assert str(employee.contract_expiry) == ("None" if explicit_clear else "2027-12-31")
    assert AuditEvent.objects.count() == (1 if explicit_clear else 0)


@pytest.mark.parametrize(
    "status,kind", [("", ""), ("kontrak", "guru"), ("freelance", ""), ("magang", "")]
)
def test_other_statuses_still_accept_expiry(hr_client, status, kind):
    response = hr_client.post(
        "/api/employees/",
        {
            "employee_code": "OTHER-01",
            "full_name": "Synthetic Employee",
            "employment_status": status,
            "pkwt_type": kind,
            "contract_expiry": "2027-12-31",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    assert response.json()["contract_expiry"] == "2027-12-31"


def preview_expiry(client, rows):
    return client.post(
        "/api/employees/import-preview/",
        {
            "file": SimpleUploadedFile(
                "employees.csv",
                (
                    "ID Karyawan,Nama Lengkap,Status Kepegawaian,Tipe PKWT,Kontrak Berakhir\n"
                    + rows
                ).encode(),
                content_type="text/csv",
            )
        },
    )


@pytest.mark.parametrize("existing", [False, True])
def test_permanent_csv_expiry_errors_prevent_entire_batch_commit(hr_client, existing):
    if existing:
        Employee.objects.create(
            employee_code="PERM-01", full_name="Synthetic Employee", employment_status="permanen"
        )
    response = preview_expiry(
        hr_client,
        "OTHER-01,Another Employee,Freelance,,2027-12-31\n"
        "PERM-01,Synthetic Employee,Permanen,,2027-12-31\n",
    )
    assert response.status_code == 201
    batch = response.json()
    assert batch["summary"]["error"] == 1
    assert "contract_expiry" in batch["rows"][1]["errors"]
    confirmed = hr_client.post(
        f"/api/employees/imports/{batch['id']}/confirm/", {}, content_type="application/json"
    )
    assert confirmed.status_code == 400
    assert Employee.objects.count() == int(existing)
    assert not AuditEvent.objects.exists()


def test_csv_transition_does_not_silently_discard_stored_expiry(hr_client):
    employee = Employee.objects.create(
        employee_code="PERM-01",
        full_name="Synthetic Employee",
        employment_status="kontrak",
        pkwt_type="guru",
        contract_expiry="2027-12-31",
    )
    batch = preview_expiry(hr_client, "PERM-01,Synthetic Employee,Permanen,,\n").json()
    assert batch["summary"]["error"] == 1
    assert "contract_expiry" in batch["rows"][0]["errors"]
    employee.refresh_from_db()
    assert str(employee.contract_expiry) == "2027-12-31"
    assert employee.employment_status == "kontrak"
    assert not AuditEvent.objects.exists()


def test_legacy_permanent_expiry_can_only_be_cleared_explicitly(hr_client):
    employee = Employee.objects.create(
        employee_code="PERM-01",
        full_name="Synthetic Employee",
        employment_status="permanen",
        contract_expiry="2027-12-31",
    )
    before = hr_client.get(f"/api/employees/{employee.pk}/")
    assert before.json()["contract_expiry"] == "2027-12-31"
    rejected = hr_client.patch(
        f"/api/employees/{employee.pk}/", {"full_name": "Changed"}, content_type="application/json"
    )
    assert rejected.status_code == 400 and "contract_expiry" in rejected.json()
    employee.refresh_from_db()
    assert str(employee.contract_expiry) == "2027-12-31"
    assert employee.full_name == "Synthetic Employee"
    assert not AuditEvent.objects.exists()
    cleared = hr_client.patch(
        f"/api/employees/{employee.pk}/", {"contract_expiry": None}, content_type="application/json"
    )
    assert cleared.status_code == 200 and cleared.json()["contract_expiry"] is None
    employee.refresh_from_db()
    assert employee.contract_expiry is None
    assert AuditEvent.objects.count() == 1


def test_permanent_create_allows_missing_or_null_expiry(hr_client):
    for number, extra in enumerate(({}, {"contract_expiry": None})):
        response = hr_client.post(
            "/api/employees/",
            {
                "employee_code": f"PERM-{number}",
                "full_name": "Synthetic Employee",
                "employment_status": "permanen",
                **extra,
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        assert response.json()["contract_expiry"] is None
    assert Employee.objects.count() == 2


def test_pre_fix_import_preview_is_revalidated_before_commit(hr_client):
    batch = preview_expiry(hr_client, "PERM-01,Synthetic Employee,Freelance,,2027-12-31\n").json()
    stored = EmployeeImportBatch.objects.get(pk=batch["id"])
    stored.rows[0]["incoming"]["employment_status"] = "permanen"
    stored.save(update_fields=["rows"])
    response = hr_client.post(
        f"/api/employees/imports/{batch['id']}/confirm/", {}, content_type="application/json"
    )
    assert response.status_code == 400 and "contract_expiry" in response.json()
    assert not Employee.objects.exists()
    assert not AuditEvent.objects.exists()
    stored.refresh_from_db()
    assert stored.committed_at is None and stored.result is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("status_write", ["patch", "import"])
def test_expiry_patch_waits_for_status_write_before_validation(
    hr_client, monkeypatch, status_write
):
    import time
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from threading import Event

    from django.db import connection, connections
    from employees.serializers import EmployeeSerializer

    employee = Employee.objects.create(
        employee_code="PERM-01",
        full_name="Synthetic Employee",
        employment_status="kontrak",
        pkwt_type="guru",
    )
    batch = (
        preview_expiry(hr_client, "PERM-01,Synthetic Employee,Permanen,,\n").json()
        if status_write == "import"
        else None
    )
    status_validated, release, expiry_validated = Event(), Event(), Event()
    pids = Queue()
    original = EmployeeSerializer.is_valid

    def pause_status(serializer, *args, **kwargs):
        result = original(serializer, *args, **kwargs)
        if serializer.initial_data.get("employment_status") == "permanen":
            status_validated.set()
            assert release.wait(20)
        if serializer.initial_data == {"contract_expiry": "2027-12-31"}:
            expiry_validated.set()
        return result

    monkeypatch.setattr(EmployeeSerializer, "is_valid", pause_status)

    def send_status():
        connections.close_all()
        try:
            worker = Client()
            worker.cookies = hr_client.cookies.copy()
            if batch:
                return worker.post(
                    f"/api/employees/imports/{batch['id']}/confirm/",
                    {},
                    content_type="application/json",
                )
            return worker.patch(
                f"/api/employees/{employee.pk}/",
                {"employment_status": "permanen"},
                content_type="application/json",
            )
        finally:
            connections.close_all()

    def send_expiry():
        connections.close_all()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids.put(cursor.fetchone()[0])
            worker = Client()
            worker.cookies = hr_client.cookies.copy()
            return worker.patch(
                f"/api/employees/{employee.pk}/",
                {"contract_expiry": "2027-12-31"},
                content_type="application/json",
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(send_status)
        try:
            assert status_validated.wait(20)
            second = pool.submit(send_expiry)
            pid = pids.get(timeout=20)
            deadline = time.monotonic() + 10
            blocked = False
            while time.monotonic() < deadline and not second.done():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s", [pid]
                    )
                    blocked = cursor.fetchone() == ("Lock",)
                if blocked:
                    break
                time.sleep(0.01)
            assert blocked, "Expiry PATCH must wait for the status writer"
            assert not expiry_validated.is_set(), (
                "Expiry must be validated after acquiring the lock"
            )
        finally:
            release.set()
        status_response = first.result(timeout=25)
        expiry_response = second.result(timeout=25)
    assert status_response.status_code == 200
    assert expiry_response.status_code == 400
    assert "contract_expiry" in expiry_response.json()
    employee.refresh_from_db()
    assert employee.employment_status == "permanen"
    assert employee.contract_expiry is None
    assert AuditEvent.objects.count() == 1
