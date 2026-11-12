import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client
from employees.models import Employee

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_hr(django_user_model):
    user = django_user_model.objects.create_user(email="magang@example.test")
    user.groups.add(Group.objects.get_or_create(name="HR")[0])
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.parametrize("extra", [{}, {"pkwt_type": ""}, {"pkwt_type": "yayasan"}])
def test_magang_employee_uses_fixed_yayasan_type(client_hr, extra):
    response = client_hr.post(
        "/api/employees/",
        {
            "employee_code": "INTERN-01",
            "full_name": "Synthetic Intern",
            "employment_status": "magang",
            **extra,
        },
        content_type="application/json",
    )
    assert response.status_code == 201, response.content
    assert response.json()["pkwt_type"] == "yayasan"
    assert Employee.objects.get().pkwt_type == "yayasan"
    assert AuditEvent.objects.get().action == "employee.created"


def test_magang_to_kontrak_requires_a_deliberate_type_selection(client_hr):
    employee = Employee.objects.create(
        employee_code="INTERN-01",
        full_name="Synthetic Intern",
        employment_status="magang",
        pkwt_type="yayasan",
    )
    response = client_hr.patch(
        f"/api/employees/{employee.pk}/",
        {"employment_status": "kontrak"},
        content_type="application/json",
    )
    assert response.status_code == 400 and "pkwt_type" in response.json()
    employee.refresh_from_db()
    assert employee.employment_status == "magang"
    assert not AuditEvent.objects.exists()


@pytest.mark.parametrize("kind", ["guru", "klinik_umum"])
def test_conflicting_magang_type_is_rejected(client_hr, kind):
    response = client_hr.post(
        "/api/employees/",
        {
            "employee_code": "INTERN-01",
            "full_name": "Synthetic Intern",
            "employment_status": "magang",
            "pkwt_type": kind,
        },
        content_type="application/json",
    )
    assert response.status_code == 400 and "pkwt_type" in response.json()
    assert not Employee.objects.exists() and not AuditEvent.objects.exists()


@pytest.mark.parametrize(
    "status,kind", [("kontrak", "guru"), ("permanen", ""), ("freelance", ""), ("", "")]
)
def test_magang_transitions_apply_the_target_status_type(client_hr, status, kind):
    employee = Employee.objects.create(
        employee_code="INTERN-01",
        full_name="Synthetic Intern",
        employment_status="magang",
        pkwt_type="yayasan",
    )
    data = {"employment_status": status}
    if status == "kontrak":
        data["pkwt_type"] = kind
    response = client_hr.patch(
        f"/api/employees/{employee.pk}/", data, content_type="application/json"
    )
    assert response.status_code == 200, response.content
    assert (response.json()["employment_status"], response.json()["pkwt_type"]) == (status, kind)


def test_kontrak_to_magang_replaces_previous_type_and_preserves_expiry(client_hr):
    employee = Employee.objects.create(
        employee_code="INTERN-01",
        full_name="Synthetic Employee",
        employment_status="kontrak",
        pkwt_type="guru",
        contract_expiry="2027-12-31",
    )
    response = client_hr.patch(
        f"/api/employees/{employee.pk}/",
        {"employment_status": "magang"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["pkwt_type"] == "yayasan"
    assert response.json()["contract_expiry"] == "2027-12-31"


def test_csv_magang_default_is_shown_and_persisted_at_confirmation(client_hr):
    from django.core.files.uploadedfile import SimpleUploadedFile

    response = client_hr.post(
        "/api/employees/import-preview/",
        {
            "file": SimpleUploadedFile(
                "employees.csv",
                b"ID Karyawan,Nama Lengkap,Status Kepegawaian,Tipe PKWT\n"
                b"INTERN-01,Synthetic Intern,Magang,\n",
                content_type="text/csv",
            )
        },
    )
    assert response.status_code == 201
    batch = response.json()
    assert batch["summary"]["error"] == 0
    assert batch["rows"][0]["incoming"]["pkwt_type"] == "yayasan"
    confirmed = client_hr.post(
        f"/api/employees/imports/{batch['id']}/confirm/", {}, content_type="application/json"
    )
    assert confirmed.status_code == 200
    assert Employee.objects.get().pkwt_type == "yayasan"


@pytest.mark.parametrize("kind", ["", "guru", "klinik_umum"])
def test_database_rejects_non_yayasan_magang_type(kind):
    from django.db import IntegrityError, transaction

    with pytest.raises(IntegrityError), transaction.atomic():
        Employee.objects.create(
            employee_code="INTERN-01",
            full_name="Synthetic Intern",
            employment_status="magang",
            pkwt_type=kind,
        )


@pytest.mark.django_db(transaction=True)
def test_magang_migration_backfills_only_type_and_is_reversible():
    from datetime import date

    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    assert connection.settings_dict["NAME"].startswith("test_")
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    old = [("employees", "0008_employment_classification")]
    executor.migrate(old)
    try:
        historical = executor.loader.project_state(old).apps.get_model("employees", "Employee")
        intern = historical.objects.create(
            employee_code="INTERN-01",
            full_name="Synthetic Intern",
            employment_status="magang",
            job_title="Guru",
            start_date=date(2026, 1, 1),
            contract_expiry=date(2026, 12, 31),
        )
        control = historical.objects.create(
            employee_code="OTHER-01",
            full_name="Synthetic Other",
            employment_status="kontrak",
            pkwt_type="guru",
        )
        before = list(historical.objects.order_by("employee_code").values())
        MigrationExecutor(connection).migrate(latest)
        after = list(Employee.objects.order_by("employee_code").values())
        expected = [
            {**row, "pkwt_type": "yayasan"} if row["id"] == intern.pk else row for row in before
        ]
        assert after == expected
        MigrationExecutor(connection).migrate(old)
        assert historical.objects.get(pk=intern.pk).pkwt_type == ""
        assert historical.objects.get(pk=control.pk).pkwt_type == "guru"
    finally:
        MigrationExecutor(connection).migrate(latest)
