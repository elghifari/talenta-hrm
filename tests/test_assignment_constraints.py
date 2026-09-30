from datetime import date

import pytest
from django.db import IntegrityError, transaction
from employees.models import Employee, EmployeeAssignment
from organization.models import Unit


@pytest.mark.django_db
@pytest.mark.parametrize(
    "start,end",
    [
        (date(2020, 1, 1), date(2020, 1, 1)),
        (date(2020, 2, 1), date(2020, 1, 1)),
        (date(2020, 1, 15), date(2020, 3, 1)),
        (date(2020, 1, 15), None),
    ],
)
def test_database_rejects_invalid_or_overlapping_assignment_periods(start, end):
    employee = Employee.objects.create(employee_code="0001", full_name="Synthetic Employee")
    unit = Unit.objects.create(code="A", name="Synthetic Unit")
    EmployeeAssignment.objects.create(
        employee=employee,
        unit=unit,
        effective_from=date(2020, 1, 1),
        effective_until=date(2020, 2, 1),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        EmployeeAssignment.objects.create(
            employee=employee, unit=unit, effective_from=start, effective_until=end
        )


@pytest.mark.django_db
def test_adjacent_assignments_preserve_transfer_boundary():
    employee = Employee.objects.create(employee_code="0001", full_name="Synthetic Employee")
    unit = Unit.objects.create(code="A", name="Synthetic Unit")
    EmployeeAssignment.objects.create(
        employee=employee,
        unit=unit,
        effective_from=date(2020, 1, 1),
        effective_until=date(2020, 2, 1),
    )
    EmployeeAssignment.objects.create(employee=employee, unit=unit, effective_from=date(2020, 2, 1))
    assert employee.assignments.count() == 2
