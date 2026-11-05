import uuid

import pytest
from audit.models import AuditEvent
from contracts.models import ContractDraft
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


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
def test_non_hr_denied_all_contract_endpoints(django_user_model, role, staff, superuser, active):
    user = django_user_model.objects.create_user(
        email="restricted@example.test", is_staff=staff, is_superuser=superuser, is_active=active
    )
    if role:
        user.groups.add(Group.objects.get_or_create(name=role)[0])
    client = APIClient()
    client.force_authenticate(user)
    ident = uuid.uuid4()
    for path in [
        "/api/contract-references/",
        "/api/contract-drafts/?employee=" + str(ident),
        f"/api/contract-drafts/{ident}/",
    ]:
        assert client.get(path).status_code == 403
    assert client.post("/api/contract-drafts/", {}, format="json").status_code == 403
    assert client.patch(f"/api/contract-drafts/{ident}/", {}, format="json").status_code == 403
    assert ContractDraft.objects.count() == AuditEvent.objects.count() == 0


def test_anonymous_denied():
    assert APIClient().get("/api/contract-references/").status_code == 403


def test_real_session_csrf_required(hr_user, employee, reference_bundle):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(hr_user)
    payload = {"id": str(uuid.uuid4()), "employee": str(employee.id), "values": {}}
    assert client.post("/api/contract-drafts/", payload, format="json").status_code == 403
    client.get("/api/auth/csrf/")
    response = client.post(
        "/api/contract-drafts/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert response.status_code == 201


def test_unconfigured_references_do_not_break_personnel(hr_client, settings, tmp_path):
    settings.CONTRACT_REFERENCE_ROOT = tmp_path
    assert hr_client.get("/api/contract-references/").data["available"] is False
    assert hr_client.get("/api/employees/").status_code == 200
