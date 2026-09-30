from django.conf import settings
from django.db import models


class Unit(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )


class UnitAccess(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "unit"], name="unique_user_unit_access"),
        ]
