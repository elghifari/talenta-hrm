from datetime import date
from uuid import uuid4

import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client
from employees.models import Employee, EmployeeAssignment
from organization.models import Branch, Division, Unit, UnitAccess
from test_employee_grouping import hr as hr

pytestmark = pytest.mark.django_db


def choices(client):
    branch = client.post(
        "/api/organization/branches/", {"name": "Cabang Contoh"}, content_type="application/json"
    ).json()
    division = client.post(
        "/api/organization/divisions/",
        {"name": "Divisi Contoh", "branch": branch["id"]},
        content_type="application/json",
    ).json()
    return branch, division


def test_hr_assigns_and_clears_primary_groups_without_touching_unit_grants(hr):
    client, user = hr
    branch, division = choices(client)
    original = Employee.objects.create(
        employee_code="0005", full_name="Synthetic Existing", job_title="Terapis"
    )
    assert not UnitAccess.objects.exists() and not EmployeeAssignment.objects.exists()
    response = client.patch(
        f"/api/employees/{original.pk}/",
        {"branch": branch["id"], "division": division["id"]},
        content_type="application/json",
    )
    assert response.status_code == 200
    detail = client.get(f"/api/employees/{original.pk}/").json()
    assert detail["branch"] == branch["id"] and detail["branch_name"] == branch["name"]
    assert detail["division"] == division["id"] and detail["division_name"] == division["name"]
    original.refresh_from_db()
    assert str(original.branch_id) == branch["id"] and original.job_title == "Terapis"
    bad = client.patch(
        f"/api/employees/{original.pk}/", {"branch": str(uuid4())}, content_type="application/json"
    )
    assert bad.status_code == 400
    assert (
        client.patch(
            f"/api/employees/{original.pk}/",
            {"branch": None, "division": None},
            content_type="application/json",
        ).status_code
        == 200
    )
    original.refresh_from_db()
    assert original.branch_id is None and original.division_id is None
    assert original.job_title == "Terapis" and original.employee_code == "0005"
    assert not UnitAccess.objects.exists() and not EmployeeAssignment.objects.exists()
    events = AuditEvent.objects.filter(action="employee.updated")
    assert events.count() == 2 and all(event.actor_id == user.pk for event in events)


def test_manager_grouping_is_read_only_and_cannot_expand_unit_scope(hr, django_user_model):
    client, _ = hr
    branch, division = choices(client)
    fields = {
        "branch": branch["id"],
        "division": division["id"],
        "date_of_birth": "1996-04-12",
        "job_title": "Private title",
    }
    employee = client.post(
        "/api/employees/",
        {"employee_code": "0011", "full_name": "Visible", **fields},
        content_type="application/json",
    )
    assert employee.status_code == 201
    outside = client.post(
        "/api/employees/",
        {"employee_code": "0012", "full_name": "Outside", **fields},
        content_type="application/json",
    ).json()
    manager = django_user_model.objects.create_user(email="grouping-manager@example.test")
    manager.groups.add(Group.objects.get_or_create(name="KEPALA_UNIT")[0])
    reader = Client(enforce_csrf_checks=True)
    reader.force_login(manager)
    assert reader.get("/api/employees/").json() == []
    unit = Unit.objects.create(code="GROUP-UNIT", name="Scoped unit")
    UnitAccess.objects.create(user=manager, unit=unit)
    EmployeeAssignment.objects.create(
        employee_id=employee.json()["id"], unit=unit, effective_from=date(2020, 1, 1)
    )
    visible = reader.get("/api/employees/").json()
    assert [item["employee_code"] for item in visible] == ["0011"]
    assert visible[0]["branch_name"] == "Cabang Contoh"
    assert visible[0]["division_name"] == "Divisi Contoh"
    assert not {
        "date_of_birth",
        "job_title",
        "level",
        "start_date",
        "contract_expiry",
    }.intersection(visible[0])
    assert reader.get(f"/api/employees/{outside['id']}/").status_code == 404
    token = reader.get("/api/auth/csrf/").json()["csrfToken"]
    before = AuditEvent.objects.count()
    assert (
        reader.patch(
            f"/api/employees/{employee.json()['id']}/",
            {"branch": None},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 403
    )
    assert AuditEvent.objects.count() == before


@pytest.mark.parametrize("role", ["KEPALA_UNIT", "FINANCE", "TECHNICAL_ADMIN", "INTERN", None])
def test_reference_management_denies_non_hr_with_valid_csrf(hr, django_user_model, role):
    client, _ = hr
    branch, division = choices(client)
    account = django_user_model.objects.create_user(
        email="grouping-denied@example.test", is_superuser=role is None
    )
    if role:
        account.groups.add(Group.objects.get_or_create(name=role)[0])
    denied = Client(enforce_csrf_checks=True)
    denied.force_login(account)
    token = denied.get("/api/auth/csrf/").json()["csrfToken"]
    before = AuditEvent.objects.count()
    for kind, record in [("branches", branch), ("divisions", division)]:
        url = f"/api/organization/{kind}/"
        assert denied.get(url).status_code == 403
        assert (
            denied.post(
                url,
                {"name": "Unauthorized"},
                content_type="application/json",
                HTTP_X_CSRFTOKEN=token,
            ).status_code
            == 403
        )
        assert (
            denied.patch(
                url + record["id"] + "/",
                {"name": "Unauthorized"},
                content_type="application/json",
                HTTP_X_CSRFTOKEN=token,
            ).status_code
            == 403
        )
        assert client.get(url).json() == [record]
    assert Branch.objects.count() == 1 and Division.objects.count() == 1
    assert AuditEvent.objects.count() == before


@pytest.mark.parametrize("kind", ["branches", "divisions"])
def test_reference_names_reject_duplicates_blank_and_unknown_fields(hr, kind):
    client, _ = hr
    url = f"/api/organization/{kind}/"
    owner = {"branch": str(Branch.objects.create(name="Owner").pk)} if kind == "divisions" else {}
    first = client.post(
        url, {"name": "  Cabang   Contoh ", **owner}, content_type="application/json"
    )
    assert first.status_code == 201
    for data in [
        {"name": "cabang contoh"},
        {"name": " \t "},
        {"name": "x" * 151},
        {"name": "Other", "id": str(uuid4())},
    ]:
        assert (
            client.post(url, {**data, **owner}, content_type="application/json").status_code == 400
        )
    assert len(client.get(url).json()) == 1
    assert AuditEvent.objects.count() == 1
