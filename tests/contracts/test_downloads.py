import uuid
from hashlib import sha256

import pytest
from audit.models import AuditEvent
from contracts.services import create_draft, generate_document
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def generated(hr_user, employee, reference_bundle, contract_values):
    draft = create_draft(
        actor=hr_user, draft_id=uuid.uuid4(), employee_id=employee.id, values=contract_values
    )
    return generate_document(actor=hr_user, draft_id=draft.id, expected_revision=1)


def test_download_exact_bytes_and_no_render_on_get(hr_client, generated, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("GET must not render")

    monkeypatch.setattr("contracts.services.render_docx", fail)
    count = AuditEvent.objects.count()
    response = hr_client.get(f"/api/contract-documents/{generated.id}/download/")
    content = b"".join(response.streaming_content)
    assert sha256(content).hexdigest() == generated.content_sha256
    assert response["Content-Type"] == generated.mime_type
    assert "attachment;" in response["Content-Disposition"]
    assert hr_client.get(f"/api/contract-drafts/{generated.draft_id}/documents/").status_code == 200
    assert AuditEvent.objects.count() == count


@pytest.mark.parametrize(
    "role,staff,superuser,active",
    [
        (None, False, False, True),
        ("FINANCE", False, False, True),
        ("KEPALA_UNIT", False, False, True),
        (None, True, False, True),
        (None, True, True, True),
        ("HR", False, False, False),
    ],
)
def test_current_permissions_guard_download_and_history(
    generated, django_user_model, role, staff, superuser, active
):
    user = django_user_model.objects.create_user(
        email="download-restricted@example.test",
        is_staff=staff,
        is_superuser=superuser,
        is_active=active,
    )
    if role:
        user.groups.add(Group.objects.get_or_create(name=role)[0])
    client = APIClient()
    client.force_authenticate(user)
    for path in [
        f"/api/contract-documents/{generated.id}/download/",
        f"/api/contract-drafts/{generated.draft_id}/documents/",
    ]:
        assert client.get(path).status_code == 403
    assert (
        client.post(
            f"/api/contract-drafts/{generated.draft_id}/generate/",
            {"expected_revision": 1},
            format="json",
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "name", ["x\r\nInjected: yes", "../../name/file", "Nama 😀 日本", "x" * 10000]
)
def test_filename_is_safe(name):
    from contracts.services import safe_filename

    filename = safe_filename(name, uuid.uuid4(), 1)
    assert filename.endswith(".docx")
    assert len(filename) <= 200
    assert not any(c in filename for c in "\r\n/\\")
