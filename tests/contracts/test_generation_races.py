import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from audit.models import AuditEvent
from contracts.models import ContractDocument
from contracts.services import create_draft, generate_document
from django.db import close_old_connections


@pytest.mark.django_db(transaction=True)
def test_duplicate_concurrent_generation_commits_one_artifact(
    hr_user, employee, reference_bundle, contract_values
):
    draft = create_draft(
        actor=hr_user, draft_id=uuid.uuid4(), employee_id=employee.id, values=contract_values
    )
    barrier = Barrier(2)

    def generate(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return generate_document(actor=hr_user, draft_id=draft.id, expected_revision=1).id
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(generate, range(2)))
    assert ids[0] == ids[1]
    assert ContractDocument.objects.count() == 1
    assert AuditEvent.objects.filter(action="contract.document_generated").count() == 1
