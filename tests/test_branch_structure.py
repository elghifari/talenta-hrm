import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client
from employees.models import Employee
from organization.models import Branch, Division
from test_employee_grouping import hr as hr

pytestmark = pytest.mark.django_db


@pytest.fixture
def structure():
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    employee = Employee.objects.create(
        employee_code="0007", full_name="Synthetic Employee", branch=branch, division=division
    )
    payload = {
        "name": "Renamed Branch",
        "divisions": [
            {"id": str(division.pk), "name": "Renamed Division"},
            {"name": "New Division"},
        ],
        "deleted": [],
        "expected": {"name": branch.name, "divisions": {str(division.pk): division.name}},
    }
    return branch, division, employee, payload


def save(client, branch, payload):
    return client.patch(
        f"/api/organization/branches/{branch.pk}/structure/",
        payload,
        content_type="application/json",
    )


def test_combined_save_preserves_employee_identity_and_records_actor(hr, structure):
    client, actor = hr
    branch, division, employee, payload = structure
    response = save(client, branch, payload)
    assert response.status_code == 200, response.content
    branch.refresh_from_db()
    division.refresh_from_db()
    employee.refresh_from_db()
    assert branch.name == payload["name"]
    assert division.name == "Renamed Division"
    assert set(Division.objects.values_list("name", flat=True)) == {
        "Renamed Division",
        "New Division",
    }
    assert (employee.employee_code, employee.branch_id, employee.division_id) == (
        "0007",
        branch.pk,
        division.pk,
    )
    assert set(AuditEvent.objects.values_list("action", flat=True)) == {
        "branch.updated",
        "division.updated",
        "division.created",
    }
    assert not AuditEvent.objects.exclude(actor=actor).exists()


@pytest.mark.parametrize("invalid", ["duplicate", "foreign", "omitted", "stale"])
def test_invalid_combined_save_changes_nothing(hr, structure, invalid):
    client, _ = hr
    branch, division, employee, payload = structure
    if invalid == "duplicate":
        payload["divisions"][1]["name"] = "renamed division"
    elif invalid == "foreign":
        other = Branch.objects.create(name="Other")
        foreign = Division.objects.create(name="Foreign", branch=other)
        payload["divisions"][0]["id"] = str(foreign.pk)
    elif invalid == "omitted":
        payload["divisions"] = []
    else:
        payload["expected"]["name"] = "Outdated"
    before = list(Division.objects.values_list("pk", "name", "branch_id"))
    response = save(client, branch, payload)
    assert response.status_code == (409 if invalid == "stale" else 400)
    branch.refresh_from_db()
    employee.refresh_from_db()
    assert branch.name == "Synthetic Branch"
    assert list(Division.objects.values_list("pk", "name", "branch_id")) == before
    assert employee.division_id == division.pk
    assert AuditEvent.objects.count() == 0


def test_delete_populated_division_keeps_branch_and_employee(hr, structure):
    client, actor = hr
    branch, division, employee, payload = structure
    impact = client.get(f"/api/organization/divisions/{division.pk}/deletion-impact/")
    assert impact.status_code == 200
    assert impact.json() == {"employee_count": 1}
    division_id = division.pk
    payload["divisions"] = []
    payload["deleted"] = [{"id": str(division_id), "employee_count": 1}]
    response = save(client, branch, payload)
    assert response.status_code == 200, response.content
    employee.refresh_from_db()
    assert employee.branch_id == branch.pk
    assert employee.division_id is None
    assert employee.employee_code == "0007"
    assert not Division.objects.filter(pk=division_id).exists()
    assert Employee.objects.count() == 1
    assert AuditEvent.objects.filter(
        actor=actor, action="division.deleted", target_id=division_id
    ).exists()
    assert AuditEvent.objects.filter(
        actor=actor, action="employee.updated", target_id=employee.pk
    ).exists()


def test_changed_population_requires_confirmation_again(hr, structure):
    client, _ = hr
    branch, division, employee, payload = structure
    payload["divisions"] = []
    payload["deleted"] = [{"id": str(division.pk), "employee_count": 0}]
    response = save(client, branch, payload)
    assert response.status_code == 409
    employee.refresh_from_db()
    assert employee.division_id == division.pk
    assert Division.objects.filter(pk=division.pk).exists()
    assert AuditEvent.objects.count() == 0


def test_manager_cannot_read_population_or_save_structure(django_user_model, structure):
    user = django_user_model.objects.create_user(email="structure-manager@example.test")
    user.groups.add(Group.objects.get_or_create(name="KEPALA_UNIT")[0])
    client = Client()
    client.force_login(user)
    branch, division, employee, payload = structure
    assert (
        client.get(f"/api/organization/divisions/{division.pk}/deletion-impact/").status_code == 403
    )
    assert save(client, branch, payload).status_code == 403
    employee.refresh_from_db()
    assert employee.division_id == division.pk
    assert AuditEvent.objects.count() == 0
