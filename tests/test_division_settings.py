import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client
from employees.models import Employee
from organization.models import Branch, Division
from test_employee_grouping import hr as hr

pytestmark = pytest.mark.django_db


def payload_for(branch, divisions):
    return {
        "name": branch.name,
        "divisions": [
            {
                "id": str(item.pk),
                "name": item.name,
                "kinerja_enabled": False,
                "pelimpahan_enabled": False,
            }
            for item in divisions
        ],
        "deleted": [],
        "expected": {
            "name": branch.name,
            "divisions": {str(item.pk): item.name for item in divisions},
            "settings": {
                str(item.pk): {"kinerja_enabled": False, "pelimpahan_enabled": False}
                for item in divisions
            },
        },
    }


def save(client, branch, payload):
    return client.patch(
        f"/api/organization/branches/{branch.pk}/structure/",
        payload,
        content_type="application/json",
    )


def test_hr_saves_independent_settings_with_attributable_old_and_new_audit(hr):
    client, actor = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    first = Division.objects.create(name="Synthetic First", branch=branch)
    second = Division.objects.create(name="Synthetic Second", branch=branch)
    payload = payload_for(branch, [first, second])
    payload["divisions"][0]["kinerja_enabled"] = True
    payload["divisions"][1]["pelimpahan_enabled"] = True

    response = save(client, branch, payload)

    assert response.status_code == 200, response.content
    rows = {item["id"]: item for item in response.json()["divisions"]}
    assert rows[str(first.pk)]["kinerja_enabled"] is True
    assert rows[str(first.pk)]["pelimpahan_enabled"] is False
    assert rows[str(second.pk)]["kinerja_enabled"] is False
    assert rows[str(second.pk)]["pelimpahan_enabled"] is True
    first.refresh_from_db()
    second.refresh_from_db()
    assert (first.kinerja_enabled, first.pelimpahan_enabled) == (True, False)
    assert (second.kinerja_enabled, second.pelimpahan_enabled) == (False, True)
    assert AuditEvent.objects.count() == 2
    event = AuditEvent.objects.get(target_id=first.pk)
    assert event.actor_id == actor.pk
    assert event.action == "division.settings_changed"
    assert event.created_at is not None
    assert event.changes == {"kinerja_enabled": {"old": False, "new": True}}
    assert AuditEvent.objects.get(target_id=second.pk).changes == {
        "pelimpahan_enabled": {"old": False, "new": True}
    }
    detail = client.get(f"/api/organization/divisions/{first.pk}/").json()
    assert detail["kinerja_enabled"] is True
    assert detail["pelimpahan_enabled"] is False


def test_settings_default_off_noop_does_not_audit_and_disabling_preserves_employees(hr):
    client, _ = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    employee = Employee.objects.create(
        employee_code="0001", full_name="Synthetic Employee", branch=branch, division=division
    )
    assert division.kinerja_enabled is False
    assert division.pelimpahan_enabled is False
    payload = payload_for(branch, [division])
    assert save(client, branch, payload).status_code == 200
    assert AuditEvent.objects.count() == 0
    payload["divisions"][0]["kinerja_enabled"] = True
    assert save(client, branch, payload).status_code == 200
    payload["expected"]["settings"][str(division.pk)]["kinerja_enabled"] = True
    assert save(client, branch, payload).status_code == 200
    assert AuditEvent.objects.count() == 1
    payload["divisions"][0]["kinerja_enabled"] = False
    assert save(client, branch, payload).status_code == 200
    assert AuditEvent.objects.count() == 2
    assert AuditEvent.objects.order_by("pk").last().changes == {
        "kinerja_enabled": {"old": True, "new": False}
    }
    employee.refresh_from_db()
    assert employee.division_id == division.pk
    assert employee.branch_id == branch.pk


@pytest.mark.parametrize("bad", [None, 0, 1, "true", "false", [], {}])
def test_non_boolean_settings_reject_entire_combined_edit(hr, bad):
    client, _ = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    payload = payload_for(branch, [division])
    payload["name"] = "Must Not Persist"
    payload["divisions"][0].update(kinerja_enabled=True, pelimpahan_enabled=bad)
    assert save(client, branch, payload).status_code == 400
    branch.refresh_from_db()
    division.refresh_from_db()
    assert branch.name == "Synthetic Branch"
    assert division.kinerja_enabled is False
    assert division.pelimpahan_enabled is False
    assert AuditEvent.objects.count() == 0


def test_stale_settings_cannot_overwrite_newer_change(hr):
    client, _ = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    stale = payload_for(branch, [division])
    fresh = payload_for(branch, [division])
    fresh["divisions"][0]["kinerja_enabled"] = True
    assert save(client, branch, fresh).status_code == 200
    stale["divisions"][0]["pelimpahan_enabled"] = True
    assert save(client, branch, stale).status_code == 409
    division.refresh_from_db()
    assert (division.kinerja_enabled, division.pelimpahan_enabled) == (True, False)
    assert AuditEvent.objects.count() == 1


def test_settings_require_snapshot_and_cannot_bypass_audit_through_direct_patch(hr):
    client, _ = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    payload = payload_for(branch, [division])
    del payload["expected"]["settings"]
    payload["divisions"][0]["kinerja_enabled"] = True
    assert save(client, branch, payload).status_code == 400
    assert (
        client.patch(
            f"/api/organization/divisions/{division.pk}/",
            {"kinerja_enabled": True},
            content_type="application/json",
        ).status_code
        == 400
    )
    division.refresh_from_db()
    assert division.kinerja_enabled is False
    assert AuditEvent.objects.count() == 0


@pytest.mark.parametrize(
    "role", [None, "KEPALA_UNIT", "FINANCE", "TECHNICAL_ADMIN", "INTERN", "superuser"]
)
def test_non_hr_cannot_write_settings_even_with_valid_csrf(django_user_model, role):
    user = django_user_model.objects.create_user(email="denied-settings@example.test")
    if role == "superuser":
        user.is_superuser = True
        user.is_staff = True
        user.save()
    elif role:
        user.groups.add(Group.objects.get_or_create(name=role)[0])
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    token = client.get("/api/auth/csrf/").json()["csrfToken"]
    client.defaults["HTTP_X_CSRFTOKEN"] = token
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    payload = payload_for(branch, [division])
    payload["divisions"][0]["kinerja_enabled"] = True
    assert save(client, branch, payload).status_code == 403
    division.refresh_from_db()
    assert division.kinerja_enabled is False
    assert AuditEvent.objects.count() == 0


def test_anonymous_and_missing_csrf_cannot_change_settings(hr):
    _, actor = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    payload = payload_for(branch, [division])
    payload["divisions"][0]["kinerja_enabled"] = True
    client = Client(enforce_csrf_checks=True)
    assert save(client, branch, payload).status_code == 403
    client.force_login(actor)
    assert save(client, branch, payload).status_code == 403
    division.refresh_from_db()
    assert division.kinerja_enabled is False
    assert AuditEvent.objects.count() == 0


def test_audit_failure_rolls_back_settings_and_branch_changes(hr, monkeypatch):
    client, _ = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    payload = payload_for(branch, [division])
    payload["name"] = "Must Roll Back"
    payload["divisions"][0]["kinerja_enabled"] = True
    original = AuditEvent.objects.create

    def fail_settings_audit(**kwargs):
        if kwargs["action"] == "division.settings_changed":
            raise RuntimeError("Synthetic audit failure")
        return original(**kwargs)

    monkeypatch.setattr(AuditEvent.objects, "create", fail_settings_audit)
    with pytest.raises(RuntimeError, match="Synthetic audit failure"):
        save(client, branch, payload)
    branch.refresh_from_db()
    division.refresh_from_db()
    assert branch.name == "Synthetic Branch"
    assert division.kinerja_enabled is False
    assert AuditEvent.objects.count() == 0


def test_new_division_settings_are_saved_and_audited(hr):
    client, actor = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    payload = payload_for(branch, [])
    payload["divisions"] = [{"name": "Synthetic New", "pelimpahan_enabled": True}]
    assert save(client, branch, payload).status_code == 200
    division = Division.objects.get()
    assert (division.kinerja_enabled, division.pelimpahan_enabled) == (False, True)
    event = AuditEvent.objects.get(action="division.settings_changed")
    assert event.actor_id == actor.pk
    assert event.target_id == division.pk
    assert event.changes == {"pelimpahan_enabled": {"old": False, "new": True}}


def test_legacy_name_only_structure_edits_preserve_enabled_settings(hr):
    client, _ = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    payload = payload_for(branch, [division])
    payload["divisions"][0].update(kinerja_enabled=True, pelimpahan_enabled=True)
    assert save(client, branch, payload).status_code == 200
    legacy = {
        "name": "Synthetic Renamed Branch",
        "divisions": [{"id": str(division.pk), "name": "Synthetic Renamed Division"}],
        "deleted": [],
        "expected": {"name": branch.name, "divisions": {str(division.pk): division.name}},
    }
    assert save(client, branch, legacy).status_code == 200
    division.refresh_from_db()
    assert (division.kinerja_enabled, division.pelimpahan_enabled) == (True, True)
    assert division.name == "Synthetic Renamed Division"
    assert AuditEvent.objects.filter(action="division.settings_changed").count() == 1


def test_direct_division_creation_cannot_set_flags_without_snapshot_and_settings_audit(hr):
    client, _ = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    response = client.post(
        "/api/organization/divisions/",
        {"branch": str(branch.pk), "name": "Synthetic Bypass", "kinerja_enabled": True},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert Division.objects.count() == 0
    assert AuditEvent.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_simultaneous_settings_saves_accept_only_one_reviewed_snapshot(hr):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connections

    _, actor = hr
    branch = Branch.objects.create(name="Synthetic Concurrent Branch")
    division = Division.objects.create(name="Synthetic Concurrent Division", branch=branch)
    barrier = Barrier(2)

    def attempt(flag):
        try:
            client = Client()
            client.force_login(actor)
            payload = payload_for(branch, [division])
            payload["divisions"][0][flag] = True
            barrier.wait(timeout=10)
            return save(client, branch, payload).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["kinerja_enabled", "pelimpahan_enabled"]))
    assert sorted(results) == [200, 409]
    division.refresh_from_db()
    assert division.kinerja_enabled != division.pelimpahan_enabled
    assert AuditEvent.objects.filter(action="division.settings_changed").count() == 1


@pytest.mark.django_db(transaction=True)
def test_name_only_patch_cannot_restore_stale_settings_without_audit(hr, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from django.db import connections
    from organization.serializers import DivisionSerializer

    client, _ = hr
    branch = Branch.objects.create(name="Synthetic Branch")
    division = Division.objects.create(name="Synthetic Division", branch=branch)
    validated, release = Event(), Event()
    original = DivisionSerializer.is_valid

    def pause_after_validation(serializer, *args, **kwargs):
        result = original(serializer, *args, **kwargs)
        assert serializer.instance.kinerja_enabled is False
        assert serializer.instance.pelimpahan_enabled is False
        validated.set()
        assert release.wait(timeout=15)
        return result

    monkeypatch.setattr(DivisionSerializer, "is_valid", pause_after_validation)

    def rename():
        connections.close_all()
        try:
            worker = Client()
            worker.cookies = client.cookies.copy()
            return worker.patch(
                f"/api/organization/divisions/{division.pk}/",
                {"name": "Synthetic Renamed"},
                content_type="application/json",
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(rename)
        try:
            assert validated.wait(timeout=10)
            payload = payload_for(branch, [division])
            payload["divisions"][0].update(kinerja_enabled=True, pelimpahan_enabled=True)
            assert save(client, branch, payload).status_code == 200
        finally:
            release.set()
        response = pending.result(timeout=10)
    assert response.status_code == 200
    division.refresh_from_db()
    assert division.name == "Synthetic Renamed"
    assert (division.kinerja_enabled, division.pelimpahan_enabled) == (True, True)
    assert response.json()["kinerja_enabled"] is True
    assert response.json()["pelimpahan_enabled"] is True
    assert AuditEvent.objects.filter(action="division.settings_changed").count() == 1
    assert AuditEvent.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_settings_migrations_preserve_existing_division_and_audit():
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    assert connection.settings_dict["NAME"].startswith("test_")
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    previous = [("organization", "0005_require_division_branch"), ("audit", "0001_initial")]
    try:
        executor.migrate(previous)
        apps = executor.loader.project_state(previous).apps
        branch = apps.get_model("organization", "Branch").objects.create(name="Synthetic Existing")
        division = apps.get_model("organization", "Division").objects.create(
            name="Synthetic Existing Division", branch_id=branch.pk
        )
        actor = apps.get_model("accounts", "User").objects.create(email="migration@example.test")
        event = apps.get_model("audit", "AuditEvent").objects.create(
            actor_id=actor.pk, action="division.created", target_id=division.pk
        )
        MigrationExecutor(connection).migrate(latest)
        division = Division.objects.get(pk=division.pk)
        assert division.branch_id == branch.pk
        assert division.name == "Synthetic Existing Division"
        assert (division.kinerja_enabled, division.pelimpahan_enabled) == (False, False)
        restored_event = AuditEvent.objects.get(pk=event.pk)
        assert restored_event.changes == {}
        assert restored_event.created_at == event.created_at
        assert restored_event.actor_id == actor.pk
        assert restored_event.target_id == division.pk
    finally:
        MigrationExecutor(connection).migrate(latest)
