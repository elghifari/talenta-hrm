import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client
from employees.models import Employee


@pytest.mark.django_db
def test_hr_updates_employee_identity_with_audit_event(django_user_model):
    hr = django_user_model.objects.create_user(email="hr@example.test")
    hr.groups.add(Group.objects.create(name="HR"))
    employee = Employee.objects.create(employee_code="0001", full_name="Synthetic Original")
    client = Client()
    client.force_login(hr)
    response = client.patch(
        f"/api/employees/{employee.pk}/",
        {"full_name": "Synthetic Corrected"},
        content_type="application/json",
    )
    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.full_name == "Synthetic Corrected"
    event = AuditEvent.objects.get()
    assert event.action == "employee.updated"
    assert event.target_id == employee.pk
    assert event.actor == hr
