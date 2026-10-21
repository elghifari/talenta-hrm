import uuid

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models


class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee_code = models.CharField(max_length=64, unique=True)
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField(null=True, blank=True)
    job_title = models.CharField(max_length=200, blank=True, default="")
    level = models.CharField(max_length=100, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    contract_expiry = models.DateField(null=True, blank=True)


class EmployeeAssignment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="assignments")
    unit = models.ForeignKey("organization.Unit", on_delete=models.PROTECT)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(effective_until__isnull=True)
                | models.Q(effective_until__gt=models.F("effective_from")),
                name="valid_assignment_period",
            ),
            ExclusionConstraint(
                name="no_overlapping_employee_assignments",
                expressions=[
                    ("employee", RangeOperators.EQUAL),
                    (
                        models.Func(
                            "effective_from",
                            "effective_until",
                            models.Value("[)"),
                            function="DATERANGE",
                            output_field=DateRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
            ),
        ]
