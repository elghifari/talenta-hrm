from uuid import uuid4

from audit.models import AuditEvent
from django.db import IntegrityError, transaction
from employees.models import Employee
from employees.permissions import HRPermission
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Branch, Division
from .serializers import BranchSerializer, DivisionSerializer


class ReferenceViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, HRPermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def handle_exception(self, error):
        cause = error.__cause__ if isinstance(error, IntegrityError) else None
        name = self.queryset.model._meta.model_name
        constraint = (
            "unique_division_name_per_branch_ci" if name == "division" else "unique_branch_name_ci"
        )
        if (
            getattr(cause, "sqlstate", None) == "23505"
            and cause.diag.table_name == self.queryset.model._meta.db_table
            and cause.diag.constraint_name == constraint
        ):
            error = ValidationError({"name": ["Nama sudah digunakan."]})
        return super().handle_exception(error)

    @transaction.atomic
    def perform_create(self, serializer):
        if serializer.Meta.model is Division:
            Branch.objects.select_for_update().get(pk=serializer.validated_data["branch"].pk)
        record = serializer.save()
        AuditEvent.objects.create(
            actor=self.request.user,
            action=f"{record._meta.model_name}.created",
            target_id=record.pk,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        if serializer.Meta.model is Division:
            Branch.objects.select_for_update().get(pk=serializer.instance.branch_id)
        record = serializer.save()
        AuditEvent.objects.create(
            actor=self.request.user,
            action=f"{record._meta.model_name}.updated",
            target_id=record.pk,
        )


class BranchViewSet(ReferenceViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer

    @action(detail=True, methods=["patch"], url_path="structure")
    @transaction.atomic
    def structure(self, request, pk=None):
        branch = self.get_queryset().select_for_update().get(pk=self.get_object().pk)
        current = list(Division.objects.select_for_update().filter(branch=branch))
        data = request.data
        expected = {"name": branch.name, "divisions": {str(item.pk): item.name for item in current}}
        if not isinstance(data, dict) or set(data) != {"name", "divisions", "expected", "deleted"}:
            raise ValidationError({"name": ["Data cabang tidak valid."]})
        if data["expected"] != expected:
            return Response(
                {"name": ["Data telah berubah. Tutup editor dan buka kembali."]}, status=409
            )
        field = serializers.CharField(max_length=150, allow_blank=False)
        name = " ".join(field.run_validation(data["name"]).split())
        if not name or Branch.objects.exclude(pk=branch.pk).filter(name__iexact=name).exists():
            raise ValidationError({"name": ["Nama cabang kosong atau sudah digunakan."]})
        rows = data["divisions"]
        if not isinstance(rows, list) or len(rows) > 500:
            raise ValidationError({"name": ["Daftar divisi tidak valid (maksimal 500)."]})
        known = {str(item.pk): item for item in current}
        deleted = data["deleted"]
        if not isinstance(deleted, list):
            raise ValidationError({"name": ["Daftar penghapusan tidak valid."]})
        removals = {}
        for entry in deleted:
            if not isinstance(entry, dict) or set(entry) != {"id", "employee_count"}:
                raise ValidationError({"name": ["Konfirmasi penghapusan tidak valid."]})
            identifier = entry["id"]
            if not isinstance(identifier, str) or identifier not in known or identifier in removals:
                raise ValidationError({"name": ["Divisi yang dihapus tidak valid."]})
            affected = list(Employee.objects.select_for_update().filter(division_id=identifier))
            if type(entry["employee_count"]) is not int or entry["employee_count"] != len(affected):
                return Response(
                    {
                        "name": [
                            "Jumlah karyawan berubah. Batalkan dan konfirmasi penghapusan kembali."
                        ]
                    },
                    status=409,
                )
            removals[identifier] = affected
        seen, names, changes = set(), set(), []
        for row in rows:
            if not isinstance(row, dict) or set(row) - {"id", "name"}:
                raise ValidationError({"name": ["Data divisi tidak valid."]})
            identifier = row.get("id")
            if identifier is not None and (
                not isinstance(identifier, str)
                or identifier not in known
                or identifier in seen
                or identifier in removals
            ):
                raise ValidationError({"name": ["Divisi tidak valid untuk cabang ini."]})
            value = " ".join(field.run_validation(row.get("name")).split())
            if not value or value.lower() in names:
                raise ValidationError({"name": ["Nama divisi kosong atau duplikat."]})
            names.add(value.lower())
            if identifier:
                seen.add(identifier)
            changes.append((known.get(identifier), value))
        if seen | set(removals) != set(known):
            raise ValidationError({"name": ["Penghapusan divisi harus dikonfirmasi."]})
        for identifier, affected in removals.items():
            for employee in affected:
                employee.division = None
                employee.save(update_fields=["division"])
                AuditEvent.objects.create(
                    actor=request.user, action="employee.updated", target_id=employee.pk
                )
            known[identifier].delete()
            AuditEvent.objects.create(
                actor=request.user, action="division.deleted", target_id=identifier
            )
        if branch.name != name:
            branch.name = name
            branch.save(update_fields=["name"])
            AuditEvent.objects.create(
                actor=request.user, action="branch.updated", target_id=branch.pk
            )
        renamed = [(item, value) for item, value in changes if item and item.name != value]
        for item, value in renamed:
            Division.objects.filter(pk=item.pk).update(name=str(uuid4()))
        for item, value in changes:
            if item is None:
                item = Division.objects.create(branch=branch, name=value)
                AuditEvent.objects.create(
                    actor=request.user, action="division.created", target_id=item.pk
                )
            elif any(record.pk == item.pk for record, _ in renamed):
                item.name = value
                item.save(update_fields=["name"])
                AuditEvent.objects.create(
                    actor=request.user, action="division.updated", target_id=item.pk
                )
        return Response(
            {
                "branch": BranchSerializer(branch).data,
                "divisions": DivisionSerializer(
                    Division.objects.filter(branch=branch), many=True
                ).data,
            }
        )


class DivisionViewSet(ReferenceViewSet):
    queryset = Division.objects.select_related("branch")
    serializer_class = DivisionSerializer

    @action(detail=True, methods=["get"], url_path="deletion-impact")
    def deletion_impact(self, request, pk=None):
        division = self.get_object()
        return Response({"employee_count": Employee.objects.filter(division=division).count()})
