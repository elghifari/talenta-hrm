from datetime import date
from decimal import Decimal

import pytest
from django.apps import apps
from django.contrib.auth.models import Group
from django.test import Client
from employees.models import Employee


@pytest.mark.django_db
def test_hr_reads_effective_dated_compensation_history(django_user_model):
    assert apps.is_installed("compensation"), "Compensation history is missing"
    CompensationAssignment = apps.get_model("compensation", "CompensationAssignment")
    employee = Employee.objects.create(employee_code="0007", full_name="Synthetic Employee")
    CompensationAssignment.objects.create(
        employee=employee,
        component_code="GAJI_POKOK",
        amount=Decimal("1600000.00"),
        effective_from=date(2020, 1, 1),
        effective_until=date(2020, 2, 1),
    )
    CompensationAssignment.objects.create(
        employee=employee,
        component_code="GAJI_POKOK",
        amount=Decimal("1700000.00"),
        effective_from=date(2020, 2, 1),
    )
    hr = django_user_model.objects.create_user(email="hr@example.test")
    hr.groups.add(Group.objects.create(name="HR"))
    client = Client()
    client.force_login(hr)
    response = client.get(f"/api/employees/{employee.pk}/compensation/")
    assert response.status_code == 200
    assert [row["amount"] for row in response.json()] == ["1700000.00", "1600000.00"]
    assert response.json()[1]["effective_until"] == "2020-02-01"
    assert "amount" not in client.get(f"/api/employees/{employee.pk}/").json()
