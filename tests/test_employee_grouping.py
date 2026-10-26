import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client

pytestmark = pytest.mark.django_db


@pytest.fixture
def hr(django_user_model):
    user = django_user_model.objects.create_user(email="grouping-hr@example.test")
    user.groups.add(Group.objects.get_or_create(name="HR")[0])
    client = Client()
    client.force_login(user)
    return client, user


def test_hr_manages_controlled_branch_and_division_choices(hr):
    client, user = hr
    branch_id = None
    for kind, action in [("branches", "branch"), ("divisions", "division")]:
        endpoint = f"/api/organization/{kind}/"
        listed = client.get(endpoint)
        assert listed.status_code == 200
        assert listed.json() == []
        payload = {"name": "  Pilihan   Contoh "}
        if kind == "divisions":
            payload["branch"] = branch_id
        created = client.post(endpoint, payload, content_type="application/json")
        assert created.status_code == 201
        choice = created.json()
        if kind == "branches":
            branch_id = choice["id"]
        assert choice["name"] == "Pilihan Contoh"
        assert client.get(endpoint).json() == [choice]
        renamed = client.patch(
            endpoint + choice["id"] + "/", {"name": "Nama Baru"}, content_type="application/json"
        )
        assert renamed.status_code == 200
        assert client.get(endpoint).json()[0]["name"] == "Nama Baru"
        events = AuditEvent.objects.filter(action__startswith=f"{action}.")
        assert set(events.values_list("action", flat=True)) == {
            f"{action}.created",
            f"{action}.updated",
        }
        assert all(
            event.actor_id == user.pk and str(event.target_id) == choice["id"] for event in events
        )
