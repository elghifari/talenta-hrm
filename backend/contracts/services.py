import re
from hashlib import sha256

from audit.models import AuditEvent
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from employees.models import Employee
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from .constants import MIME, TOKENS
from .formatting import compile_tokens
from .models import ContractDocument, ContractDraft
from .prefill import apply_job_default, apply_unit_default, prefill_employee
from .references import KINDS, ReferenceUnavailable, load_reference_bundle
from .renderer import InvalidTemplate, render_docx
from .validation import validate_values

UNSET = object()


class RevisionConflict(APIException):
    status_code = 409

    def __init__(self, revision):
        self.detail = {"code": "revision_conflict", "revision": revision}


class ReferenceFailure(APIException):
    status_code = 503
    default_detail = {
        "code": "reference_unavailable",
        "detail": "Referensi kontrak belum tersedia.",
    }


class DraftExists(APIException):
    status_code = 409
    default_detail = {"code": "draft_exists"}


def require_hr(actor):
    if not (actor.is_authenticated and actor.is_active and actor.groups.filter(name="HR").exists()):
        raise PermissionDenied()


def reference(version=None):
    try:
        return load_reference_bundle(version)
    except ReferenceUnavailable as exc:
        raise ReferenceFailure() from exc


def selections(bundle, kind, unit, job):
    if unit:
        apply_unit_default(bundle, unit, kind)
    if job:
        apply_job_default(bundle, job, kind)
        row = bundle.jobs[job.strip().casefold()]
        if not unit or row["unit"].strip().casefold() != unit.strip().casefold():
            raise ValidationError({"job_default_key": ["Jabatan tidak sesuai Unit sumber."]})


def record_contract_audit(actor, action, draft, changed):
    AuditEvent.objects.create(
        actor=actor,
        action=action,
        target_id=draft.id,
        changes={
            "draft": str(draft.id),
            "employee": str(draft.employee_id),
            "revision": draft.revision,
            "pkwt_type": draft.pkwt_type,
            "template_sha256": draft.template_sha256,
            "fields": sorted(changed),
        },
    )


@transaction.atomic
def create_draft(
    *,
    actor,
    draft_id,
    employee_id,
    pkwt_type=None,
    source_unit=UNSET,
    job_default_key=UNSET,
    values=None,
):
    require_hr(actor)
    employee = get_object_or_404(Employee.objects.select_for_update(), pk=employee_id)
    if employee.employment_status not in {"kontrak", "magang"}:
        raise ValidationError({"employee": ["Draf PKWT hanya untuk pegawai Kontrak atau Magang."]})
    kind = employee.pkwt_type if pkwt_type is None else pkwt_type
    if kind not in KINDS:
        raise ValidationError({"pkwt_type": ["Pilih tipe PKWT yang akan dibuat."]})
    bundle = reference()
    prefill = prefill_employee(employee, bundle, kind)
    if source_unit is UNSET:
        source_unit = prefill["source_unit"]
    if job_default_key is UNSET:
        job_default_key = (
            prefill["job_default_key"] if source_unit == prefill["source_unit"] else None
        )
    selections(bundle, kind, source_unit, job_default_key)
    supplied = validate_values(kind, values, complete=False)
    checked = validate_values(kind, {**prefill["values"], **supplied}, complete=False)
    try:
        with transaction.atomic():
            draft = ContractDraft.objects.create(
                id=draft_id,
                employee=employee,
                created_by=actor,
                updated_by=actor,
                pkwt_type=kind,
                reference_version=bundle.version,
                template_sha256=bundle.template_sha256(kind),
                employee_snapshot=prefill["employee_snapshot"],
                source_unit=source_unit,
                job_default_key=job_default_key,
                values=checked,
            )
    except IntegrityError as exc:
        if ContractDraft.objects.filter(pk=draft_id).exists():
            raise DraftExists() from exc
        raise
    record_contract_audit(actor, "contract.draft_created", draft, checked.keys())
    return draft


def changed_editable_fields(draft, changes, next_values):
    changed = [
        key
        for key in ("source_unit", "job_default_key")
        if key in changes and changes[key] != getattr(draft, key)
    ]
    changed += [
        key
        for key in set(draft.values) | set(next_values)
        if draft.values.get(key) != next_values.get(key)
    ]
    return changed


def apply_editable_changes(draft, changes, next_values):
    for key in ("source_unit", "job_default_key"):
        if key in changes:
            setattr(draft, key, changes[key])
    draft.values = next_values


@transaction.atomic
def update_draft(*, actor, draft_id, expected_revision, changes):
    require_hr(actor)
    if set(changes) - {"source_unit", "job_default_key", "values"}:
        raise ValidationError({"detail": ["Isian tidak dikenal."]})
    draft = get_object_or_404(ContractDraft.objects.select_for_update(), pk=draft_id)
    if draft.revision != expected_revision:
        raise RevisionConflict(draft.revision)
    checked = validate_values(draft.pkwt_type, changes.get("values", draft.values), complete=False)
    changed = changed_editable_fields(draft, changes, checked)
    if not changed:
        return draft
    if {"source_unit", "job_default_key"} & set(changed):
        selections(
            reference(draft.reference_version),
            draft.pkwt_type,
            changes.get("source_unit", draft.source_unit),
            changes.get("job_default_key", draft.job_default_key),
        )
    apply_editable_changes(draft, changes, checked)
    draft.revision += 1
    draft.updated_by = actor
    draft.save()
    record_contract_audit(actor, "contract.draft_updated", draft, changed)
    return draft


def safe_filename(name, draft_id, revision):
    cleaned = re.sub(r"[^\w .-]", "", name, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")[:80] or "pegawai"
    return f"PKWT-{cleaned}-{str(draft_id)[:8]}-r{revision}.docx"


@transaction.atomic
def generate_document(*, actor, draft_id, expected_revision):
    require_hr(actor)
    draft = get_object_or_404(ContractDraft.objects.select_for_update(), pk=draft_id)
    if draft.revision != expected_revision:
        raise RevisionConflict(draft.revision)
    existing = ContractDocument.objects.filter(
        draft=draft, revision=draft.revision, template_sha256=draft.template_sha256
    ).first()
    if existing is not None:
        return existing
    bundle = reference(draft.reference_version)
    if bundle.template_sha256(draft.pkwt_type) != draft.template_sha256:
        raise ReferenceFailure()
    tokens = compile_tokens(draft.pkwt_type, draft.values)
    try:
        content = render_docx(
            bundle.template_bytes(draft.pkwt_type), tokens, TOKENS[draft.pkwt_type]
        )
    except (ReferenceUnavailable, InvalidTemplate) as exc:
        raise ReferenceFailure() from exc
    document = ContractDocument.objects.create(
        draft=draft,
        generated_by=actor,
        revision=draft.revision,
        reference_version=draft.reference_version,
        pkwt_type=draft.pkwt_type,
        template_sha256=draft.template_sha256,
        input_snapshot=draft.values,
        token_snapshot=tokens,
        filename=safe_filename(draft.values["nama"], draft.id, draft.revision),
        mime_type=MIME,
        content_sha256=sha256(content).hexdigest(),
        content=content,
    )
    record_contract_audit(actor, "contract.document_generated", draft, [])
    return document
