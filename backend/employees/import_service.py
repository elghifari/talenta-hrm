from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import APIException

from .imports import parse_rows, summarize
from .models import EmployeeImportBatch


class PreviewExpired(APIException):
    status_code = 410
    default_detail = "Pratinjau kedaluwarsa. Unggah CSV kembali."


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


def create_preview(request, upload):
    rows = parse_rows(upload, request)
    return EmployeeImportBatch.objects.create(
        owner=request.user,
        session_fingerprint=session_fingerprint(request),
        expires_at=timezone.now() + timedelta(minutes=15),
        rows=rows,
    )
