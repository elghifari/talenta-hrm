from collections.abc import Mapping

from audit.models import AuditEvent
from compensation.serializers import CompensationSerializer
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from organization.models import UnitAccess
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Employee
from .permissions import EmployeePermission, HRPermission
from .serializers import EmployeeSerializer


class EmployeeViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    http_method_names = ["get", "post", "patch", "head", "options"]
    serializer_class = EmployeeSerializer
    permission_classes = [EmployeePermission]

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as error:
            if not self._is_employee_code_conflict(error):
                raise
            raise ValidationError(
                {"employee_code": ["employee with this employee code already exists."]}
            ) from error

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except IntegrityError as error:
            if not self._is_employee_code_conflict(error):
                raise
            raise ValidationError(
                {"employee_code": ["employee with this employee code already exists."]}
            ) from error

    @staticmethod
    def _is_employee_code_conflict(error):
        cause = error.__cause__
        return (
            getattr(cause, "sqlstate", None) == "23505"
            and cause.diag.table_name == Employee._meta.db_table
            and cause.diag.constraint_name == "employees_employee_employee_code_key"
        )

    @action(detail=True, methods=["get"], permission_classes=[HRPermission])
    def compensation(self, request, pk=None):
        employee = self.get_object()
        history = employee.compensation_assignments.order_by("-effective_from", "component_code")
        return Response(CompensationSerializer(history, many=True).data)

    @transaction.atomic
    def perform_create(self, serializer):
        employee = serializer.save()
        AuditEvent.objects.create(
            actor=self.request.user, action="employee.created", target_id=employee.pk
        )

    @transaction.atomic
    def perform_update(self, serializer):
        employee = serializer.save()
        AuditEvent.objects.create(
            actor=self.request.user, action="employee.updated", target_id=employee.pk
        )

    def get_queryset(self):
        employees = Employee.objects.select_related("branch", "division").order_by("employee_code")
        if (
            self.action == "partial_update"
            and isinstance(self.request.data, Mapping)
            and {"branch", "division"}.intersection(self.request.data)
        ):
            employees = employees.select_for_update(of=("self",))
        if self.request.user.groups.filter(name="HR").exists():
            return employees
        today = timezone.localdate()
        unit_ids = UnitAccess.objects.filter(user=self.request.user).values("unit_id")
        return employees.filter(
            Q(assignments__effective_until__isnull=True)
            | Q(assignments__effective_until__gt=today),
            assignments__effective_from__lte=today,
            assignments__unit_id__in=unit_ids,
        ).distinct()
