import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from audit.models import AuditEvent
from contracts.models import ContractDraft
from contracts.services import RevisionConflict, create_draft, update_draft
from django.db import close_old_connections


@pytest.mark.django_db(transaction=True)
def test_same_revision_concurrent_writes_one_wins(hr_user, employee, reference_bundle):
    draft = create_draft(actor=hr_user, draft_id=uuid.uuid4(), employee_id=employee.id, values={})
    barrier = Barrier(2)

    def update(nip):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                update_draft(
                    actor=hr_user,
                    draft_id=draft.id,
                    expected_revision=1,
                    changes={"values": {"nip": nip}},
                )
                return 200
            except RevisionConflict:
                return 409
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(update, ["0001", "0002"]))
    assert sorted(outcomes) == [200, 409]
    assert ContractDraft.objects.get(pk=draft.id).revision == 2
    assert AuditEvent.objects.filter(action="contract.draft_updated").count() == 1
