from datetime import date
from decimal import Decimal

import pytest
from compensation.models import CompensationAssignment
from django.db import IntegrityError, transaction
from employees.models import Employee


@pytest.mark.django_db
@pytest.mark.parametrize(
    "amount,start,end",
    [
        (Decimal("-1"), date(2020, 3, 1), None),
        (Decimal("100"), date(2020, 3, 1), date(2020, 3, 1)),
        (Decimal("100"), date(2020, 1, 15), None),
    ],
)
def test_database_rejects_invalid_compensation_periods(amount, start, end):
    employee = Employee.objects.create(employee_code="0001", full_name="Synthetic Employee")
    CompensationAssignment.objects.create(
        employee=employee,
        component_code="GAJI_POKOK",
        amount=Decimal("100"),
        effective_from=date(2020, 1, 1),
        effective_until=date(2020, 2, 1),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        CompensationAssignment.objects.create(
            employee=employee,
            component_code="GAJI_POKOK",
            amount=amount,
            effective_from=start,
            effective_until=end,
        )
