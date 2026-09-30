from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models


class CompensationAssignment(models.Model):
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.PROTECT, related_name="compensation_assignments"
    )
    component_code = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="nonnegative_compensation"
            ),
            models.CheckConstraint(
                condition=models.Q(effective_until__isnull=True)
                | models.Q(effective_until__gt=models.F("effective_from")),
                name="valid_compensation_period",
            ),
            ExclusionConstraint(
                name="no_overlapping_compensation_components",
                expressions=[
                    ("employee", RangeOperators.EQUAL),
                    ("component_code", RangeOperators.EQUAL),
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
