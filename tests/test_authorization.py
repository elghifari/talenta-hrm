from datetime import date
from decimal import Decimal

import pytest
from audit.models import AuditEvent
from compensation.models import CompensationAssignment
from django.contrib.auth.models import Group
from django.test import Client
from employees.models import Employee, EmployeeAssignment
from organization.models import Unit, UnitAccess


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["KEPALA_UNIT", "FINANCE", "TECHNICAL_ADMIN", "INTERN", None])
def test_non_hr_accounts_cannot_write_employees_or_read_compensation(django_user_model, role):
    user = django_user_model.objects.create_user(email="restricted@example.test")
    if role:
        user.groups.add(Group.objects.create(name=role))
    employee = Employee.objects.create(employee_code="0001", full_name="Synthetic Employee")
    unit = Unit.objects.create(code="A", name="Synthetic Unit")
    EmployeeAssignment.objects.create(employee=employee, unit=unit, effective_from=date(2020, 1, 1))
    UnitAccess.objects.create(user=user, unit=unit)
    CompensationAssignment.objects.create(
        employee=employee,
        component_code="GAJI_POKOK",
        amount=Decimal("1234567"),
        effective_from=date(2020, 1, 1),
    )
    client = Client()
    client.force_login(user)
    assert client.get(f"/api/employees/{employee.pk}/compensation/").status_code == 403
    assert (
        client.post(
            "/api/employees/",
            {"employee_code": "0002", "full_name": "Synthetic New"},
            content_type="application/json",
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/employees/{employee.pk}/",
            {"full_name": "Synthetic Unauthorized"},
            content_type="application/json",
        ).status_code
        == 403
    )
    employee.refresh_from_db()
    assert employee.full_name == "Synthetic Employee"
    assert Employee.objects.count() == 1
    assert not AuditEvent.objects.exists()
    response = client.get("/api/employees/")
    if role == "KEPALA_UNIT":
        assert response.status_code == 200
        assert response.json() == [
            {
                "id": str(employee.pk),
                "employee_code": "0001",
                "full_name": "Synthetic Employee",
                "branch": None,
                "branch_name": None,
                "division": None,
                "division_name": None,
            }
        ]
    else:
        assert response.status_code == 403


@pytest.mark.django_db
def test_anonymous_user_cannot_read_employees():
    assert Client().get("/api/employees/").status_code == 403


@pytest.mark.django_db
def test_authenticated_write_rejects_missing_csrf(django_user_model):
    hr = django_user_model.objects.create_user(email="hr@example.test")
    hr.groups.add(Group.objects.create(name="HR"))
    client = Client(enforce_csrf_checks=True)
    client.force_login(hr)
    assert (
        client.post(
            "/api/employees/",
            {"employee_code": "0001", "full_name": "Synthetic Employee"},
            content_type="application/json",
        ).status_code
        == 403
    )
    assert not Employee.objects.exists()
