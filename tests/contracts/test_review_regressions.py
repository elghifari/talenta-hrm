import uuid

import pytest
from audit.models import AuditEvent
from contracts.models import ContractDraft
from contracts.services import create_draft

pytestmark = pytest.mark.django_db


def test_unchanged_selections_do_not_require_references_to_save_text(
    hr_user, hr_client, employee, reference_bundle, settings, tmp_path
):
    draft = create_draft(
        actor=hr_user,
        draft_id=uuid.uuid4(),
        employee_id=employee.id,
        source_unit="School",
        job_default_key=None,
        values={},
    )
    settings.CONTRACT_REFERENCE_ROOT = tmp_path / "missing"
    response = hr_client.patch(
        f"/api/contract-drafts/{draft.id}/",
        {
            "expected_revision": 1,
            "source_unit": "School",
            "job_default_key": None,
            "values": {**draft.values, "nip": "0007"},
        },
        format="json",
    )
    assert response.status_code == 200
    draft.refresh_from_db()
    assert draft.revision == 2
    assert draft.values["nip"] == "0007"
    assert AuditEvent.objects.filter(action="contract.draft_updated").count() == 1
    changed = hr_client.patch(
        f"/api/contract-drafts/{draft.id}/",
        {
            "expected_revision": 2,
            "source_unit": "Different Unit",
        },
        format="json",
    )
    assert changed.status_code == 503
    assert ContractDraft.objects.get(pk=draft.pk).source_unit == "School"
    assert AuditEvent.objects.filter(action="contract.draft_updated").count() == 1
