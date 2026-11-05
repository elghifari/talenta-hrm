import uuid

import pytest
from audit.models import AuditEvent
from contracts.models import ContractDraft

pytestmark = pytest.mark.django_db


def test_create_draft_preserves_employee_and_manual_nip(hr_client, reference_bundle, employee):
    before = (employee.contract_expiry, employee.employment_status, employee.pkwt_type)
    draft_id = str(uuid.uuid4())
    response = hr_client.post(
        "/api/contract-drafts/",
        {
            "id": draft_id,
            "employee": str(employee.id),
            "values": {},
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert ContractDraft.objects.get(pk=draft_id).revision == 1
    assert response.data["values"].get("nip", "") == ""
    employee.refresh_from_db()
    assert (employee.contract_expiry, employee.employment_status, employee.pkwt_type) == before
    assert AuditEvent.objects.filter(action="contract.draft_created").count() == 1


def create(client, employee):
    response = client.post(
        "/api/contract-drafts/",
        {
            "id": str(uuid.uuid4()),
            "employee": str(employee.id),
            "values": {},
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data


def test_stale_revision_is_numeric_and_does_not_overwrite(hr_client, reference_bundle, employee):
    draft = create(hr_client, employee)
    url = f"/api/contract-drafts/{draft['id']}/"
    saved = hr_client.patch(url, {"expected_revision": 1, "values": {"nip": "0007"}}, format="json")
    assert saved.status_code == 200
    conflict = hr_client.patch(url, {"expected_revision": 1, "values": {}}, format="json")
    assert conflict.status_code == 409
    assert conflict.data["revision"] == 2
    assert hr_client.get(url).data["values"] == {"nip": "0007"}
    assert AuditEvent.objects.filter(action="contract.draft_updated").count() == 1


@pytest.mark.parametrize("values", [True, [], "text", 9, None])
def test_create_rejects_non_object_values(hr_client, reference_bundle, employee, values):
    response = hr_client.post(
        "/api/contract-drafts/",
        {
            "id": str(uuid.uuid4()),
            "employee": str(employee.id),
            "values": values,
        },
        format="json",
    )
    assert response.status_code == 400
    assert ContractDraft.objects.count() == 0


def test_noop_and_duplicate_uuid_do_not_write(hr_client, reference_bundle, employee):
    draft = create(hr_client, employee)
    url = f"/api/contract-drafts/{draft['id']}/"
    assert (
        hr_client.patch(
            url, {"expected_revision": 1, "values": draft["values"]}, format="json"
        ).data["revision"]
        == 1
    )
    duplicate = hr_client.post(
        "/api/contract-drafts/",
        {
            "id": draft["id"],
            "employee": str(employee.id),
            "values": {},
        },
        format="json",
    )
    assert duplicate.status_code == 409
    assert AuditEvent.objects.count() == 1


def test_creation_prefills_exact_source_selection_when_omitted(
    hr_client, reference_bundle, employee
):
    from organization.models import Branch

    employee.branch = Branch.objects.create(name="School")
    employee.save(update_fields=["branch"])
    result = create(hr_client, employee)
    assert result["source_unit"] == "School"
    assert result["values"]["nip"] == ""


def test_list_omits_private_snapshot_and_values(hr_client, reference_bundle, employee):
    create(hr_client, employee)
    result = hr_client.get(f"/api/contract-drafts/?employee={employee.id}")
    assert result.status_code == 200
    assert result.data["count"] == 1
    assert not {"values", "employee_snapshot", "content"} & result.data["results"][0].keys()


def test_audit_failure_rolls_back_draft(hr_client, reference_bundle, employee, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("Audit unavailable")

    monkeypatch.setattr("contracts.services.record_contract_audit", fail)
    with pytest.raises(RuntimeError):
        create(hr_client, employee)
    assert ContractDraft.objects.count() == 0


def test_immutable_top_level_and_size_limit(hr_client, reference_bundle, employee):
    draft = create(hr_client, employee)
    url = f"/api/contract-drafts/{draft['id']}/"
    assert (
        hr_client.patch(
            url, {"expected_revision": 1, "employee": str(employee.id)}, format="json"
        ).status_code
        == 400
    )
    assert (
        hr_client.patch(
            url, {"expected_revision": 1, "values": {"jobdesk": "x" * 270000}}, format="json"
        ).status_code
        == 413
    )
