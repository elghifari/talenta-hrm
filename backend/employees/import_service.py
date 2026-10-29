from datetime import timedelta

from audit.models import AuditEvent
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import salted_hmac
from organization.models import Branch, Division
from rest_framework.exceptions import APIException, ValidationError

from .imports import FIELDS, parse_rows, snapshot, summarize
from .models import Employee, EmployeeImportBatch
from .serializers import EmployeeSerializer


class PreviewExpired(APIException):
    status_code = 410
    default_detail = "Pratinjau sudah kedaluwarsa. Upload ulang CSV."


def session_fingerprint(request):
    return salted_hmac(
        "employee-import", request.session.session_key or "", algorithm="sha256"
    ).hexdigest()


def get_batch(request, batch_id, *, lock=False):
    queryset = EmployeeImportBatch.objects
    if lock:
        queryset = queryset.select_for_update()
    batch = get_object_or_404(
        queryset, pk=batch_id, owner=request.user, session_fingerprint=session_fingerprint(request)
    )
    if batch.result is None and batch.expires_at <= timezone.now():
        raise PreviewExpired()
    return batch


def batch_response(batch):
    return {
        "id": str(batch.pk),
        "state": "committed" if batch.result is not None else "pending",
        "expires_at": batch.expires_at.isoformat(),
        "rows": [] if batch.result is not None else batch.rows,
        "summary": batch.result if batch.result is not None else summarize(batch.rows),
    }


def prune_batches():
    now = timezone.now()
    count, _ = EmployeeImportBatch.objects.filter(
        Q(result__isnull=True, expires_at__lte=now) | Q(committed_at__lt=now - timedelta(days=1))
    ).delete()
    return count


def create_preview(request, upload):
    prune_batches()
    rows = parse_rows(upload, request)
    return EmployeeImportBatch.objects.create(
        owner=request.user,
        session_fingerprint=session_fingerprint(request),
        expires_at=timezone.now() + timedelta(minutes=15),
        rows=rows,
    )


class ImportConflict(APIException):
    status_code = 409
    default_detail = (
        "Data berubah sejak pratinjau. Upload ulang CSV untuk melihat perubahan terbaru."
    )


def lock_hierarchy(rows):
    references = [values for row in rows for values in (row["current"], row["incoming"]) if values]
    branch_ids = {values["branch"] for values in references if values.get("branch")}
    division_ids = {values["division"] for values in references if values.get("division")}
    branches = {
        str(branch.pk): branch
        for branch in Branch.objects.select_for_update(no_key=True)
        .filter(pk__in=branch_ids)
        .order_by("pk")
    }
    divisions = {
        str(division.pk): division
        for division in Division.objects.select_for_update(no_key=True)
        .filter(pk__in=division_ids)
        .order_by("pk")
    }
    for row in rows:
        values = row["incoming"]
        branch = branches.get(values.get("branch"))
        division = divisions.get(values.get("division"))
        if values.get("branch") and (branch is None or branch.name != values.get("branch_name")):
            raise ImportConflict()
        if values.get("division") and (
            division is None
            or division.name != values.get("division_name")
            or str(division.branch_id) != values.get("branch")
        ):
            raise ImportConflict()


def commit_batch(request, batch_id):
    try:
        with transaction.atomic():
            batch = get_batch(request, batch_id, lock=True)
            if batch.result is not None:
                return batch
            if any(row["status"] == "error" for row in batch.rows):
                raise ValidationError(
                    {"detail": "Perbaiki baris bermasalah, lalu upload ulang CSV."}
                )
            lock_hierarchy(batch.rows)
            records = {
                record.employee_code: record
                for record in Employee.objects.select_for_update(of=("self",))
                .select_related("branch", "division")
                .filter(employee_code__in=[row["employee_code"] for row in batch.rows])
                .order_by("employee_code")
            }
            writes = []
            for row in batch.rows:
                current = records.get(row["employee_code"])
                reviewed = row["current"]
                if reviewed is not None:
                    # Pre-classification previews reviewed these fields as unclassified.
                    reviewed = {"employment_status": "", "pkwt_type": "", **reviewed}
                if snapshot(current) != reviewed:
                    raise ImportConflict()
                if row["status"] == "unchanged":
                    continue
                serializer = EmployeeSerializer(
                    current,
                    data={key: value for key, value in row["incoming"].items() if key in FIELDS},
                    partial=current is not None,
                    context={"request": request},
                )
                serializer.is_valid(raise_exception=True)
                writes.append((row["status"], serializer))
            for status, serializer in writes:
                employee = serializer.save()
                AuditEvent.objects.create(
                    actor=request.user,
                    action="employee.created" if status == "new" else "employee.updated",
                    target_id=employee.pk,
                )
            batch.result = summarize(batch.rows)
            batch.rows = []
            batch.committed_at = timezone.now()
            batch.save(update_fields=["result", "rows", "committed_at"])
            return batch
    except IntegrityError as error:
        cause = error.__cause__
        if (
            getattr(cause, "sqlstate", None) == "23505"
            and cause.diag.table_name == Employee._meta.db_table
            and cause.diag.constraint_name == "employees_employee_employee_code_key"
        ):
            raise ImportConflict() from error
        raise
