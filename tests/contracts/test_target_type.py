import uuid

import pytest
from audit.models import AuditEvent
from contracts.models import ContractDraft
from contracts.references import load_reference_bundle

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("kind", ["yayasan", "guru", "klinik_umum"])
def test_new_draft_uses_selected_type_without_reclassifying_employee(
    hr_client, reference_bundle, employee, kind
):
    before = (employee.employment_status, employee.pkwt_type, employee.contract_expiry)
    response = hr_client.post(
        "/api/contract-drafts/",
        {"id": str(uuid.uuid4()), "employee": str(employee.pk), "pkwt_type": kind, "values": {}},
        format="json",
    )
    assert response.status_code == 201, response.data
    draft = ContractDraft.objects.get()
    assert draft.pkwt_type == kind
    assert draft.template_sha256 == load_reference_bundle().template_sha256(kind)
    assert response.data["employee_snapshot"]["pkwt_type"] == before[1]
    employee.refresh_from_db()
    assert (employee.employment_status, employee.pkwt_type, employee.contract_expiry) == before
    assert AuditEvent.objects.get().action == "contract.draft_created"


@pytest.mark.parametrize("kind", ["yayasan", "guru", "klinik_umum"])
def test_magang_can_prepare_any_pkwt_type_without_changing_employee(
    hr_client, reference_bundle, employee, kind
):
    employee.employment_status = "magang"
    employee.save(update_fields=["employment_status"])
    response = hr_client.post(
        "/api/contract-drafts/",
        {"id": str(uuid.uuid4()), "employee": str(employee.pk), "pkwt_type": kind, "values": {}},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["pkwt_type"] == kind
    assert response.data["employee_snapshot"]["employment_status"] == "magang"
    employee.refresh_from_db()
    assert (employee.employment_status, employee.pkwt_type) == ("magang", "yayasan")


@pytest.mark.parametrize("kind", ["", None, "magang", "other"])
def test_invalid_target_type_is_rejected_without_writes(
    hr_client, reference_bundle, employee, kind
):
    response = hr_client.post(
        "/api/contract-drafts/",
        {"id": str(uuid.uuid4()), "employee": str(employee.pk), "pkwt_type": kind, "values": {}},
        format="json",
    )
    assert response.status_code == 400 and "pkwt_type" in response.data
    assert not ContractDraft.objects.exists() and not AuditEvent.objects.exists()


@pytest.mark.parametrize("status", ["permanen", "freelance", ""])
def test_type_choice_does_not_bypass_employee_eligibility(
    hr_client, reference_bundle, employee, status
):
    employee.employment_status = status
    employee.pkwt_type = ""
    employee.save(update_fields=["employment_status", "pkwt_type"])
    response = hr_client.post(
        "/api/contract-drafts/",
        {"id": str(uuid.uuid4()), "employee": str(employee.pk), "pkwt_type": "guru", "values": {}},
        format="json",
    )
    assert response.status_code == 400 and "employee" in response.data
    assert not ContractDraft.objects.exists() and not AuditEvent.objects.exists()


def test_saved_target_type_is_immutable(hr_client, reference_bundle, employee):
    response = hr_client.post(
        "/api/contract-drafts/",
        {"id": str(uuid.uuid4()), "employee": str(employee.pk), "pkwt_type": "guru", "values": {}},
        format="json",
    )
    assert response.status_code == 201
    url = f"/api/contract-drafts/{response.data['id']}/"
    changed = hr_client.patch(url, {"expected_revision": 1, "pkwt_type": "yayasan"}, format="json")
    assert changed.status_code == 400 and "pkwt_type" in changed.data
    assert hr_client.get(url).data["pkwt_type"] == "guru"
    assert AuditEvent.objects.count() == 1


def test_magang_docx_generation_does_not_promote_or_update_dates(
    hr_client, reference_bundle, employee, contract_values
):
    from datetime import date

    from contracts.models import ContractDocument

    employee.employment_status = "magang"
    employee.start_date = date(2026, 1, 1)
    employee.contract_expiry = date(2026, 11, 30)
    employee.save(update_fields=["employment_status", "start_date", "contract_expiry"])
    response = hr_client.post(
        "/api/contract-drafts/",
        {
            "id": str(uuid.uuid4()),
            "employee": str(employee.pk),
            "pkwt_type": "yayasan",
            "values": contract_values,
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    generated = hr_client.post(
        f"/api/contract-drafts/{response.data['id']}/generate/",
        {"expected_revision": 1},
        format="json",
    )
    assert generated.status_code == 200, generated.data
    assert ContractDocument.objects.count() == 1
    employee.refresh_from_db()
    assert (
        employee.employment_status,
        employee.pkwt_type,
        employee.start_date,
        employee.contract_expiry,
    ) == ("magang", "yayasan", date(2026, 1, 1), date(2026, 11, 30))


def test_selected_type_controls_prefill_not_employee_snapshot(
    hr_client, reference_bundle, employee
):
    from organization.models import Branch

    employee.branch = Branch.objects.create(name="School")
    employee.save(update_fields=["branch"])
    response = hr_client.post(
        "/api/contract-drafts/",
        {"id": str(uuid.uuid4()), "employee": str(employee.pk), "pkwt_type": "guru", "values": {}},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["values"]["saksi2_jabatan"] == "Kepala School"
    assert response.data["employee_snapshot"]["pkwt_type"] == "yayasan"
