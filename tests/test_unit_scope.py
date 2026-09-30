from datetime import date

import pytest
from django.apps import apps
from django.contrib.auth.models import Group
from django.test import Client


@pytest.mark.django_db
def test_manager_sees_only_current_employees_in_explicitly_assigned_units(django_user_model):
    assert apps.is_installed("organization"), "Effective unit assignments are missing"
    Unit = apps.get_model("organization", "Unit")
    UnitAccess = apps.get_model("organization", "UnitAccess")
    Assignment = apps.get_model("employees", "EmployeeAssignment")
    Employee = apps.get_model("employees", "Employee")
    manager = django_user_model.objects.create_user(email="manager@example.test")
    manager.groups.add(Group.objects.create(name="KEPALA_UNIT"))
    unit_a = Unit.objects.create(code="A", name="Synthetic Unit A")
    unit_b = Unit.objects.create(code="B", name="Synthetic Unit B", parent=unit_a)
    unit_c = Unit.objects.create(code="C", name="Synthetic Unit C")
    UnitAccess.objects.create(user=manager, unit=unit_a)
    UnitAccess.objects.create(user=manager, unit=unit_c)
    own = Employee.objects.create(employee_code="0001", full_name="Synthetic Own")
    other = Employee.objects.create(employee_code="0002", full_name="Synthetic Other")
    transferred = Employee.objects.create(employee_code="0003", full_name="Synthetic Transfer")
    second = Employee.objects.create(employee_code="0004", full_name="Synthetic Second")
    Assignment.objects.create(employee=own, unit=unit_a, effective_from=date(2020, 1, 1))
    Assignment.objects.create(employee=other, unit=unit_b, effective_from=date(2020, 1, 1))
    Assignment.objects.create(employee=second, unit=unit_c, effective_from=date(2020, 1, 1))
    Assignment.objects.create(
        employee=transferred,
        unit=unit_a,
        effective_from=date(2020, 1, 1),
        effective_until=date(2021, 1, 1),
    )
    Assignment.objects.create(employee=transferred, unit=unit_b, effective_from=date(2021, 1, 1))
    client = Client()
    client.force_login(manager)
    response = client.get("/api/employees/")
    assert response.status_code == 200
    assert {item["employee_code"] for item in response.json()} == {"0001", "0004"}
    assert client.get(f"/api/employees/{other.pk}/").status_code == 404
    assert client.get(f"/api/employees/{transferred.pk}/").status_code == 404
