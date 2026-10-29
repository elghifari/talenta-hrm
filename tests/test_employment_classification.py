import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client
from employees.models import Employee, EmployeeImportBatch

pytestmark = pytest.mark.django_db


@pytest.fixture
def hr(django_user_model):
    user = django_user_model.objects.create_user(email="classification@example.test")
    user.groups.add(Group.objects.get_or_create(name="HR")[0])
    client = Client()
    client.force_login(user)
    return client, user


def create(client, **extra):
    return client.post(
        "/api/employees/",
        {
            "employee_code": "0001",
            "full_name": "Synthetic Employee",
            **extra,
        },
        content_type="application/json",
    )


def patch(client, employee, **data):
    return client.patch(f"/api/employees/{employee.pk}/", data, content_type="application/json")


def preview(client, rows):
    return client.post(
        "/api/employees/import-preview/",
        {
            "file": SimpleUploadedFile(
                "employees.csv",
                ("ID Karyawan,Nama Lengkap,Status Kepegawaian,Tipe PKWT\n" + rows).encode(),
                content_type="text/csv",
            )
        },
    )


def confirm(client, batch):
    return client.post(
        f"/api/employees/imports/{batch['id']}/confirm/", {}, content_type="application/json"
    )


def test_legacy_create_is_unclassified_without_inference(hr):
    client, _ = hr
    response = create(client, job_title="Guru", contract_expiry="2027-01-01")
    assert response.status_code == 201
    assert response.json()["employment_status"] == ""
    assert response.json()["pkwt_type"] == ""


@pytest.mark.parametrize(
    "status,kind",
    [
        ("kontrak", "klinik_umum"),
        ("kontrak", "guru"),
        ("kontrak", "yayasan"),
        ("freelance", ""),
        ("magang", ""),
        ("permanen", ""),
        ("", ""),
    ],
)
def test_explicit_classification_round_trips_and_is_audited(hr, status, kind):
    client, user = hr
    response = create(client, employment_status=status, pkwt_type=kind)
    assert response.status_code == 201, response.content
    employee = Employee.objects.get()
    assert (employee.employment_status, employee.pkwt_type) == (status, kind)
    body = client.get(f"/api/employees/{employee.pk}/").json()
    assert (body["employment_status"], body["pkwt_type"]) == (status, kind)
    event = AuditEvent.objects.get()
    assert (event.actor_id, event.target_id, event.action) == (
        user.pk,
        employee.pk,
        "employee.created",
    )


@pytest.mark.parametrize(
    "data,field",
    [
        ({"employment_status": "unknown"}, "employment_status"),
        ({"employment_status": None}, "employment_status"),
        ({"employment_status": "kontrak"}, "pkwt_type"),
        ({"employment_status": "kontrak", "pkwt_type": "unknown"}, "pkwt_type"),
        ({"employment_status": "permanen", "pkwt_type": "guru"}, "pkwt_type"),
        ({"pkwt_type": "guru"}, "pkwt_type"),
        ({"pkwt_type": None}, "pkwt_type"),
    ],
)
def test_invalid_classification_has_field_error_without_writes(hr, data, field):
    client, _ = hr
    response = create(client, **data)
    assert response.status_code == 400
    assert field in response.json()
    assert not Employee.objects.exists()
    assert not AuditEvent.objects.exists()


def test_patch_type_uses_current_status_and_status_transition_clears_type(hr):
    client, _ = hr
    assert create(client, employment_status="kontrak", pkwt_type="guru").status_code == 201
    employee = Employee.objects.get()
    assert patch(client, employee, pkwt_type="yayasan").status_code == 200
    changed = patch(client, employee, employment_status="freelance")
    assert changed.status_code == 200
    assert (changed.json()["employment_status"], changed.json()["pkwt_type"]) == ("freelance", "")
    rejected = patch(client, employee, pkwt_type="guru")
    assert rejected.status_code == 400 and "pkwt_type" in rejected.json()
    employee.refresh_from_db()
    assert (employee.employment_status, employee.pkwt_type) == ("freelance", "")
    assert AuditEvent.objects.count() == 3


def test_csv_labels_normalize_and_confirm_idempotently(hr):
    client, _ = hr
    response = preview(client, "0001,Synthetic Employee, kOnTrAk , Klinik Umum \n")
    assert response.status_code == 201, response.content
    batch = response.json()
    assert batch["rows"][0]["incoming"]["employment_status"] == "kontrak"
    assert batch["rows"][0]["incoming"]["pkwt_type"] == "klinik_umum"
    assert not Employee.objects.exists() and not AuditEvent.objects.exists()
    first = confirm(client, batch)
    assert first.status_code == 200
    assert confirm(client, batch).json() == first.json()
    assert client.get(f"/api/employees/imports/{batch['id']}/").json() == first.json()
    assert AuditEvent.objects.count() == 1
    assert Employee.objects.get().pkwt_type == "klinik_umum"


def test_csv_blanks_preserve_but_non_contract_status_previews_clear(hr):
    client, _ = hr
    assert create(client, employment_status="kontrak", pkwt_type="guru").status_code == 201
    AuditEvent.objects.all().delete()
    batch = preview(client, "0001,Synthetic Employee,,\n").json()
    assert batch["rows"][0]["status"] == "unchanged"
    assert confirm(client, batch).status_code == 200
    assert not AuditEvent.objects.exists()
    batch = preview(client, "0001,Synthetic Employee, PERMANEN ,\n").json()
    row = batch["rows"][0]
    assert row["incoming"]["pkwt_type"] == ""
    assert set(row["changes"]) == {"employment_status", "pkwt_type"}
    assert confirm(client, batch).status_code == 200
    assert Employee.objects.get().pkwt_type == ""


@pytest.mark.parametrize(
    "status,kind", [("unknown", ""), ("Kontrak", "unknown"), ("Kontrak", ""), ("Magang", "Guru")]
)
def test_csv_invalid_mixed_batch_is_atomic(hr, status, kind):
    client, _ = hr
    response = preview(
        client, f"0001,Synthetic Employee,Freelance,\n0002,Another,{status},{kind}\n"
    )
    assert response.status_code == 201
    batch = response.json()
    assert batch["summary"]["error"] == 1
    assert confirm(client, batch).status_code == 400
    assert not Employee.objects.exists() and not AuditEvent.objects.exists()


def test_classification_change_invalidates_preview(hr):
    client, _ = hr
    assert create(client, employment_status="kontrak", pkwt_type="guru").status_code == 201
    employee = Employee.objects.get()
    batch = preview(client, "0001,Changed,,\n").json()
    assert patch(client, employee, pkwt_type="yayasan").status_code == 200
    assert confirm(client, batch).status_code == 409
    employee.refresh_from_db()
    assert (employee.full_name, employee.pkwt_type) == ("Synthetic Employee", "yayasan")
    assert AuditEvent.objects.count() == 2


@pytest.mark.parametrize(
    "status,kind",
    [("other", ""), ("kontrak", "other"), ("kontrak", ""), ("permanen", "guru"), ("", "guru")],
)
def test_database_rejects_invalid_classification_pairs(hr, status, kind):
    client, _ = hr
    assert create(client).status_code == 201
    employee = Employee.objects.get()
    with pytest.raises(IntegrityError), transaction.atomic():
        Employee.objects.filter(pk=employee.pk).update(employment_status=status, pkwt_type=kind)


def test_old_pending_snapshot_can_confirm_without_erasing_new_classification(hr):
    client, _ = hr
    assert create(client).status_code == 201
    batch = preview(client, "0001,Changed,,\n").json()
    stored = EmployeeImportBatch.objects.get(pk=batch["id"])
    for row in stored.rows:
        for values in (row["current"], row["incoming"]):
            for key in ("employment_status", "pkwt_type"):
                values.pop(key, None)
    stored.save(update_fields=["rows"])
    assert confirm(client, batch).status_code == 200
    assert Employee.objects.get().full_name == "Changed"


def test_old_preview_rejects_classification_added_after_review(hr):
    client, _ = hr
    assert create(client).status_code == 201
    batch = preview(client, "0001,Changed,,\n").json()
    stored = EmployeeImportBatch.objects.get(pk=batch["id"])
    for row in stored.rows:
        for values in (row["current"], row["incoming"]):
            values.pop("employment_status")
            values.pop("pkwt_type")
    stored.save(update_fields=["rows"])
    employee = Employee.objects.get()
    assert patch(client, employee, employment_status="permanen").status_code == 200
    assert confirm(client, batch).status_code == 409
    employee.refresh_from_db()
    assert (employee.full_name, employee.employment_status) == ("Synthetic Employee", "permanen")
    assert AuditEvent.objects.count() == 2


def test_manager_cannot_read_or_mutate_classification_or_import(hr, django_user_model):
    from datetime import date

    from employees.models import EmployeeAssignment
    from organization.models import Unit, UnitAccess

    client, _ = hr
    assert create(client, employment_status="kontrak", pkwt_type="guru").status_code == 201
    employee = Employee.objects.get()
    manager = django_user_model.objects.create_user(email="classification-manager@example.test")
    manager.groups.add(Group.objects.get_or_create(name="KEPALA_UNIT")[0])
    unit = Unit.objects.create(code="CLASS", name="Classification Unit")
    UnitAccess.objects.create(user=manager, unit=unit)
    EmployeeAssignment.objects.create(employee=employee, unit=unit, effective_from=date(2020, 1, 1))
    restricted = Client(enforce_csrf_checks=True)
    restricted.force_login(manager)
    token = restricted.get("/api/auth/csrf/").cookies["csrftoken"].value
    restricted.defaults["HTTP_X_CSRFTOKEN"] = token
    detail = restricted.get(f"/api/employees/{employee.pk}/")
    assert detail.status_code == 200
    for body in (detail.json(), restricted.get("/api/employees/").json()[0]):
        assert "employment_status" not in body and "pkwt_type" not in body
    assert patch(restricted, employee, employment_status="permanen").status_code == 403
    assert create(restricted, employment_status="permanen").status_code == 403
    assert preview(restricted, "0001,Synthetic Employee,Permanen,\n").status_code == 403
    employee.refresh_from_db()
    assert (employee.employment_status, employee.pkwt_type) == ("kontrak", "guru")
    assert Employee.objects.count() == 1 and AuditEvent.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_migration_preserves_legacy_values_and_does_not_infer_classification():
    from datetime import date

    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    assert connection.settings_dict["NAME"].startswith("test_")
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    old = [("employees", "0007_employee_primary_groups")]
    executor.migrate(old)
    try:
        apps = executor.loader.project_state(old).apps
        historical = apps.get_model("employees", "Employee")
        employee = historical.objects.create(
            employee_code="000077",
            full_name="Synthetic Legacy",
            job_title="Guru",
            level="Senior",
            start_date=date(2020, 1, 1),
            contract_expiry=date(2028, 1, 1),
            date_of_birth=date(1990, 1, 1),
        )
        MigrationExecutor(connection).migrate(latest)
        preserved = Employee.objects.get(pk=employee.pk)
        assert (preserved.employment_status, preserved.pkwt_type) == ("", "")
        assert (
            preserved.employee_code,
            preserved.full_name,
            preserved.job_title,
            preserved.level,
        ) == (
            "000077",
            "Synthetic Legacy",
            "Guru",
            "Senior",
        )
        assert (preserved.start_date, preserved.contract_expiry, preserved.date_of_birth) == (
            date(2020, 1, 1),
            date(2028, 1, 1),
            date(1990, 1, 1),
        )
    finally:
        MigrationExecutor(connection).migrate(latest)


@pytest.mark.django_db(transaction=True)
def test_name_patch_response_refreshes_concurrent_classification(hr, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from django.db import connections
    from employees.serializers import EmployeeSerializer

    client, _ = hr
    assert create(client).status_code == 201
    employee = Employee.objects.get()
    validated, release = Event(), Event()
    original = EmployeeSerializer.is_valid

    def pause_name(serializer, *args, **kwargs):
        result = original(serializer, *args, **kwargs)
        if serializer.initial_data == {"full_name": "Renamed"}:
            validated.set()
            assert release.wait(20)
        return result

    monkeypatch.setattr(EmployeeSerializer, "is_valid", pause_name)

    def rename():
        connections.close_all()
        try:
            worker = Client()
            worker.cookies = client.cookies.copy()
            return patch(worker, employee, full_name="Renamed")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(rename)
        try:
            assert validated.wait(20)
            assert (
                patch(
                    client, employee, employment_status="kontrak", pkwt_type="yayasan"
                ).status_code
                == 200
            )
        finally:
            release.set()
        response = future.result(timeout=25)
    assert response.status_code == 200
    assert (response.json()["employment_status"], response.json()["pkwt_type"]) == (
        "kontrak",
        "yayasan",
    )
    employee.refresh_from_db()
    assert (employee.full_name, employee.employment_status, employee.pkwt_type) == (
        "Renamed",
        "kontrak",
        "yayasan",
    )
    assert AuditEvent.objects.count() == 3


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("first_write", ["patch", "import"])
def test_type_patch_waits_for_status_write_and_revalidates_current_status(
    hr, monkeypatch, first_write
):
    import time
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from threading import Event

    from django.db import connection, connections
    from employees.serializers import EmployeeSerializer

    client, _ = hr
    assert create(client, employment_status="kontrak", pkwt_type="guru").status_code == 201
    employee = Employee.objects.get()
    batch = (
        preview(client, "0001,Synthetic Employee,Permanen,\n").json()
        if first_write == "import"
        else None
    )
    validated, release = Event(), Event()
    pids = Queue()
    original = EmployeeSerializer.is_valid

    def pause_status(serializer, *args, **kwargs):
        result = original(serializer, *args, **kwargs)
        if serializer.initial_data.get("employment_status") == "permanen":
            validated.set()
            assert release.wait(20)
        return result

    monkeypatch.setattr(EmployeeSerializer, "is_valid", pause_status)

    def send_status():
        connections.close_all()
        try:
            worker = Client()
            worker.cookies = client.cookies.copy()
            return (
                confirm(worker, batch)
                if batch
                else patch(worker, employee, employment_status="permanen")
            )
        finally:
            connections.close_all()

    def send_type():
        connections.close_all()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids.put(cursor.fetchone()[0])
            worker = Client()
            worker.cookies = client.cookies.copy()
            return patch(worker, employee, pkwt_type="yayasan")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        status_future = pool.submit(send_status)
        try:
            assert validated.wait(20)
            type_future = pool.submit(send_type)
            pid = pids.get(timeout=20)
            deadline = time.monotonic() + 10
            blocked = False
            while time.monotonic() < deadline and not type_future.done():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", [pid]
                    )
                    blocked = cursor.fetchone() == ("Lock",)
                if blocked:
                    break
                time.sleep(0.01)
            assert blocked, "Type PATCH must lock the employee before cross-field validation"
        finally:
            release.set()
        first = status_future.result(timeout=25)
        second = type_future.result(timeout=25)
    assert first.status_code == 200
    assert second.status_code == 400 and "pkwt_type" in second.json()
    employee.refresh_from_db()
    assert (employee.employment_status, employee.pkwt_type) == ("permanen", "")
    assert AuditEvent.objects.count() == 2
