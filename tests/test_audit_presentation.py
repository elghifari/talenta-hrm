import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client
from organization.models import Branch, Division


@pytest.fixture
def audit_manager(django_user_model):
    user = django_user_model.objects.create_user(email="audit-manager@example.test")
    user.groups.set([Group.objects.get_or_create(name=role)[0] for role in ("HR", "HR_MANAGER")])
    return user


@pytest.fixture
def audit_client(audit_manager):
    client = Client()
    client.force_login(audit_manager)
    return client


@pytest.mark.django_db
def test_settings_projection_drops_private_metadata(audit_client, audit_manager):
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    recorded = AuditEvent.objects.create(
        actor=audit_manager,
        action="division.settings_changed",
        target_id=division.pk,
        changes={
            "kinerja_enabled": {"old": False, "new": True},
            "salary": {"old": 1, "new": 2},
            "credential": "never-export-this",
        },
    )
    response = audit_client.get("/api/audit-events/")
    assert response.status_code == 200
    event = response.json()["results"][0]
    assert event == {
        "id": recorded.pk,
        "created_at": recorded.created_at.isoformat(),
        "actor": {"id": audit_manager.pk, "email": audit_manager.email},
        "action": "division.settings_changed",
        "action_label": "Pengaturan divisi diubah",
        "target": {"type": "division", "id": str(division.pk), "label": division.name},
        "changes": {"kinerja_enabled": {"old": False, "new": True}},
    }
    assert "never-export-this" not in response.content.decode()
    assert AuditEvent.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "changes",
    [
        None,
        [],
        "secret",
        {"kinerja_enabled": None},
        {"kinerja_enabled": {"old": 0, "new": 1}},
        {"kinerja_enabled": {"old": False, "new": {"secret": True}}},
    ],
)
def test_malformed_metadata_is_not_exposed(audit_client, audit_manager, changes):
    from uuid import uuid4

    event = AuditEvent.objects.create(
        actor=audit_manager, action="division.settings_changed", target_id=uuid4(), changes={}
    )
    if changes is not None:
        AuditEvent.objects.filter(pk=event.pk).update(changes=changes)
    else:
        event.changes = None
        from audit.presentation import safe_changes

        assert safe_changes(event) == {}
        return
    result = audit_client.get("/api/audit-events/").json()["results"][0]
    assert result["changes"] == {}
    assert result["target"]["label"] is None


@pytest.mark.django_db
def test_known_unknown_and_historical_targets_are_batched(
    audit_client, audit_manager, django_assert_num_queries
):
    from uuid import uuid4

    from audit.presentation import ACTIONS, present_events
    from employees.models import Employee

    employee = Employee.objects.create(employee_code="0099", full_name="<script>literal</script>")
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    targets = {"employee": employee.pk, "branch": branch.pk, "division": division.pk}
    for action in ACTIONS:
        AuditEvent.objects.create(
            actor=audit_manager,
            action=action,
            target_id=targets[action.split(".")[0]],
            changes={"secret": "private"},
        )
    unknown = AuditEvent.objects.create(
        actor=audit_manager,
        action="future.secret",
        target_id=uuid4(),
        changes={"secret": "private"},
    )
    audit_manager.groups.clear()
    events = list(AuditEvent.objects.select_related("actor").order_by("pk"))
    with django_assert_num_queries(3):
        projected = present_events(events)
    assert projected[-1]["action_label"] == "Aktivitas lain"
    assert projected[-1]["target"] == {
        "type": "unknown",
        "id": str(unknown.target_id),
        "label": None,
    }
    assert all(row["changes"] == {} for row in projected)
    assert projected[0]["target"]["label"] == employee.full_name
    division.delete()
    assert present_events(events)[-2]["target"]["label"] is None
    assert all(row["actor"]["email"] == audit_manager.email for row in projected)
    repeated = events * 5
    with django_assert_num_queries(3):
        assert len(present_events(repeated)) == 45
