import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client
from employees.models import Employee


@pytest.fixture
def hr_client(django_user_model):
    user = django_user_model.objects.create_user(email="records-hr@example.test")
    user.groups.add(Group.objects.get_or_create(name="HR")[0])
    client = Client()
    client.force_login(user)
    return client, user


@pytest.mark.django_db
def test_employee_persists_richer_fields(hr_client):
    client, user = hr_client
    data = {
        "employee_code": "0009",
        "full_name": "Synthetic Record",
        "date_of_birth": "1996-04-12",
        "job_title": "Terapis",
        "level": "Level 1",
        "start_date": "2024-01-01",
        "contract_expiry": "2027-12-31",
    }
    response = client.post("/api/employees/", data, content_type="application/json")
    assert response.status_code == 201
    record = Employee.objects.get(employee_code="0009")
    assert record.job_title == "Terapis"
    assert str(record.date_of_birth) == "1996-04-12"
    assert str(record.contract_expiry) == "2027-12-31"
    detail = client.get(f"/api/employees/{record.pk}/").json()
    assert {key: detail[key] for key in data} == data
    event = AuditEvent.objects.get(action="employee.created")
    assert event.actor == user and event.target_id == record.pk


@pytest.mark.django_db
@pytest.mark.parametrize(
    "extra,field",
    [
        ({"date_of_birth": "2999-01-01"}, "date_of_birth"),
        ({"start_date": "2024-01-01", "contract_expiry": "2023-12-31"}, "contract_expiry"),
    ],
)
def test_employee_rejects_invalid_date_relationships(hr_client, extra, field):
    client, _ = hr_client
    response = client.post(
        "/api/employees/",
        {"employee_code": "0090", "full_name": "Synthetic Invalid", **extra},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert field in response.json()
    assert not Employee.objects.exists()
    assert not AuditEvent.objects.exists()


@pytest.mark.django_db
def test_partial_date_update_checks_stored_start_date(hr_client):
    client, _ = hr_client
    employee = Employee.objects.create(
        employee_code="0091", full_name="Synthetic Partial", start_date="2024-01-01"
    )
    response = client.patch(
        f"/api/employees/{employee.pk}/",
        {"contract_expiry": "2023-12-31"},
        content_type="application/json",
    )
    assert response.status_code == 400
    employee.refresh_from_db()
    assert employee.contract_expiry is None
    assert not AuditEvent.objects.exists()


@pytest.mark.django_db
def test_database_rejects_contract_before_start():
    from django.db import IntegrityError, transaction

    with pytest.raises(IntegrityError), transaction.atomic():
        Employee.objects.create(
            employee_code="0092",
            full_name="Synthetic Constraint",
            start_date="2024-01-01",
            contract_expiry="2023-12-31",
        )
