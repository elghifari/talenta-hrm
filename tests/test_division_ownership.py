import pytest
from audit.models import AuditEvent
from organization.models import Branch, Division
from test_employee_grouping import hr as hr

pytestmark = pytest.mark.django_db


def test_division_names_are_unique_within_their_own_branch(hr):
    client, _ = hr
    branches = [Branch.objects.create(name=name) for name in ("KURI", "Sekolah")]
    choices = []
    for branch in branches:
        response = client.post(
            "/api/organization/divisions/",
            {"name": "  Marketing  ", "branch": str(branch.pk)},
            content_type="application/json",
        )
        assert response.status_code == 201, response.content
        choice = response.json()
        assert choice["name"] == "Marketing"
        assert choice["branch"] == str(branch.pk)
        assert choice["branch_name"] == branch.name
        assert Division.objects.get(pk=choice["id"]).branch_id == branch.pk
        choices.append(choice)
    assert choices[0]["id"] != choices[1]["id"]
    before = AuditEvent.objects.count()
    duplicate = client.post(
        "/api/organization/divisions/",
        {"name": "marketing", "branch": str(branches[0].pk)},
        content_type="application/json",
    )
    assert duplicate.status_code == 400
    assert "name" in duplicate.json()
    assert Division.objects.count() == 2
    assert AuditEvent.objects.count() == before


@pytest.mark.parametrize("change", ["create", "branch", "division", "clear_branch", "no_branch"])
def test_employee_cannot_save_a_division_outside_its_branch(hr, change):
    from employees.models import Employee

    client, _ = hr
    owner = Branch.objects.create(name="KURI")
    other = Branch.objects.create(name="Sekolah")
    division = Division.objects.create(name="Marketing", branch=owner)
    record = Employee.objects.create(
        employee_code="0007", full_name="Synthetic Employee", branch=owner, division=division
    )
    if change == "division":
        record.branch = other
        record.division = None
        record.save(update_fields=["branch", "division"])
    original = (record.branch_id, record.division_id)
    payload = {
        "create": {
            "employee_code": "0008",
            "full_name": "Synthetic New",
            "branch": str(other.pk),
            "division": str(division.pk),
        },
        "branch": {"branch": str(other.pk)},
        "division": {"division": str(division.pk)},
        "clear_branch": {"branch": None},
        "no_branch": {
            "employee_code": "0008",
            "full_name": "Synthetic New",
            "division": str(division.pk),
        },
    }[change]
    creating = change in {"create", "no_branch"}
    url = "/api/employees/" if creating else f"/api/employees/{record.pk}/"
    before = AuditEvent.objects.count()
    response = getattr(client, "post" if creating else "patch")(
        url, payload, content_type="application/json"
    )
    assert response.status_code == 400, response.content
    assert "division" in response.json()
    record.refresh_from_db()
    assert (record.branch_id, record.division_id) == original
    assert Employee.objects.count() == 1
    assert AuditEvent.objects.count() == before


def test_division_owner_cannot_be_changed_by_a_rename_request(hr):
    client, _ = hr
    owner = Branch.objects.create(name="KURI")
    other = Branch.objects.create(name="Sekolah")
    division = Division.objects.create(name="Marketing", branch=owner)
    before = AuditEvent.objects.count()
    response = client.patch(
        f"/api/organization/divisions/{division.pk}/",
        {"branch": str(other.pk)},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "branch" in response.json()
    division.refresh_from_db()
    assert division.branch_id == owner.pk
    assert AuditEvent.objects.count() == before
