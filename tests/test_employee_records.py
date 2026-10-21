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
