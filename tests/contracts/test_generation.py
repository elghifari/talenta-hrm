import shutil
import uuid
from hashlib import sha256
from io import BytesIO

import pytest
from audit.models import AuditEvent
from contracts.models import ContractDocument
from contracts.services import create_draft, generate_document, update_draft
from docx import Document

pytestmark = pytest.mark.django_db


@pytest.fixture
def complete_draft(hr_user, employee, reference_bundle, contract_values):
    return create_draft(
        actor=hr_user, draft_id=uuid.uuid4(), employee_id=employee.id, values=contract_values
    )


def test_same_revision_returns_same_stored_bytes(complete_draft, hr_user):
    first = generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=1)
    second = generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=1)
    assert second.id == first.id
    assert bytes(second.content) == bytes(first.content)
    assert ContractDocument.objects.filter(draft=complete_draft).count() == 1
    assert AuditEvent.objects.filter(action="contract.document_generated").count() == 1
    assert sha256(bytes(first.content)).hexdigest() == first.content_sha256
    assert "Synthetic text" in "\n".join(
        p.text for p in Document(BytesIO(first.content)).paragraphs
    )


def test_existing_bytes_survive_reference_loss(
    complete_draft, hr_user, hr_client, reference_bundle
):
    doc = generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=1)
    shutil.rmtree(reference_bundle)
    again = generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=1)
    assert again.id == doc.id
    response = hr_client.get(f"/api/contract-documents/{doc.id}/download/")
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == bytes(doc.content)
    assert response["Cache-Control"] == "no-store"
    assert response["X-Content-Type-Options"] == "nosniff"


def test_edited_revision_leaves_old_document_unchanged(complete_draft, hr_user):
    first = generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=1)
    old_bytes = bytes(first.content)
    update_draft(
        actor=hr_user,
        draft_id=complete_draft.id,
        expected_revision=1,
        changes={"values": {**complete_draft.values, "nama": "New text"}},
    )
    second = generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=2)
    first.refresh_from_db()
    assert bytes(first.content) == old_bytes
    assert second.id != first.id


def test_generation_audit_failure_rolls_back(complete_draft, hr_user, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("Audit unavailable")

    monkeypatch.setattr("contracts.services.record_contract_audit", fail)
    with pytest.raises(RuntimeError):
        generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=1)
    assert ContractDocument.objects.count() == 0


def test_new_generation_refuses_changed_template(complete_draft, hr_user, reference_bundle):
    from contracts.services import ReferenceFailure

    (reference_bundle / "yayasan.docx").write_bytes(b"corrupt")
    with pytest.raises(ReferenceFailure):
        generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=1)
    assert ContractDocument.objects.count() == 0
    assert AuditEvent.objects.filter(action="contract.document_generated").count() == 0


def test_renderer_failure_rolls_back(complete_draft, hr_user, monkeypatch):
    from contracts.renderer import InvalidTemplate
    from contracts.services import ReferenceFailure

    def fail(*args, **kwargs):
        raise InvalidTemplate()

    monkeypatch.setattr("contracts.services.render_docx", fail)
    with pytest.raises(ReferenceFailure):
        generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=1)
    assert ContractDocument.objects.count() == 0


def test_generation_never_changes_employee_or_payroll(complete_draft, hr_user, employee):
    from compensation.models import CompensationAssignment
    from employees.models import Employee

    before = Employee.objects.values().get(pk=employee.pk)
    compensation = list(CompensationAssignment.objects.values())
    generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=1)
    assert Employee.objects.values().get(pk=employee.pk) == before
    assert list(CompensationAssignment.objects.values()) == compensation


def test_metadata_and_audit_never_contain_private_contract_values(
    complete_draft, hr_user, hr_client
):
    import json

    from audit.presentation import present_events

    doc = generate_document(actor=hr_user, draft_id=complete_draft.id, expected_revision=1)
    receipt = hr_client.get(f"/api/contract-drafts/{complete_draft.id}/documents/")
    assert receipt.status_code == 200
    assert not {"content", "input_snapshot", "token_snapshot"} & receipt.data["results"][0].keys()
    events = list(AuditEvent.objects.select_related("actor").order_by("id"))
    rendered = present_events(events)
    assert rendered[-1]["action_label"] == "Dokumen PKWT dibuat"
    serialized = json.dumps([e.changes for e in events])
    for field in ["nip", "jalan", "gaji_pokok", "jobdesk"]:
        assert json.dumps(complete_draft.values[field]) not in serialized
    assert receipt.data["results"][0]["id"] == str(doc.id)
