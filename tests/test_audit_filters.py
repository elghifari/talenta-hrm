from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client


@pytest.fixture
def reader(django_user_model):
    user = django_user_model.objects.create_user(email="filters@example.test")
    user.groups.set([Group.objects.get_or_create(name=role)[0] for role in ("HR", "HR_MANAGER")])
    client = Client()
    client.force_login(user)
    return user, client


def record(user, at):
    event = AuditEvent.objects.create(actor=user, action="employee.created", target_id=uuid4())
    AuditEvent.objects.filter(pk=event.pk).update(created_at=at)
    return event


@pytest.mark.django_db
def test_filter_dates_use_inclusive_jakarta_day(reader):
    user, client = reader
    start = datetime(2026, 10, 26, 17, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    record(user, start - timedelta(microseconds=1))
    at_start = record(user, start)
    just_before_end = record(user, end - timedelta(microseconds=1))
    record(user, end)
    response = client.get(
        "/api/audit-events/", {"date_from": "2026-10-27", "date_to": "2026-10-27"}
    )
    assert {row["id"] for row in response.json()["results"]} == {at_start.pk, just_before_end.pk}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "params",
    [
        {"date_from": "2026-02-30"},
        {"date_to": "9999-12-31"},
        {"date_from": "20261027"},
        {"date_from": "2026-10-28", "date_to": "2026-10-27"},
        {"action": "unknown"},
        {"actor": "x" * 255},
        {"page": "0"},
        {"page": "-1"},
        {"page": "1.2"},
        {"page": "last"},
        {"page": "abc"},
        {"page": "1" * 10000},
    ],
)
def test_invalid_filters_return_safe_validation_error(reader, params):
    _, client = reader
    response = client.get("/api/audit-events/", params)
    assert response.status_code == 400
    assert "traceback" not in response.content.decode().lower()


@pytest.mark.django_db
def test_actor_action_dates_combine_and_blank_filters_are_unset(reader):
    user, client = reader
    created = record(user, datetime(2026, 10, 27, tzinfo=timezone.utc))
    updated = record(user, datetime(2026, 10, 27, tzinfo=timezone.utc))
    AuditEvent.objects.filter(pk=updated.pk).update(action="employee.updated")
    params = {"actor": " FILTERS@EXAMPLE ", "action": "employee.created", "date_from": "2026-10-27"}
    assert [x["id"] for x in client.get("/api/audit-events/", params).json()["results"]] == [
        created.pk
    ]
    assert (
        client.get(
            "/api/audit-events/", {"actor": "", "action": "", "date_from": "", "date_to": ""}
        ).json()["count"]
        == 2
    )


@pytest.mark.django_db
def test_fixed_size_pages_have_stable_tie_order_and_explicit_unavailable_page(reader):
    user, client = reader
    at = datetime(2026, 10, 27, tzinfo=timezone.utc)
    events = [record(user, at) for _ in range(51)]
    first = client.get("/api/audit-events/", {"page_size": 10000}).json()
    second = client.get("/api/audit-events/", {"page": 2}).json()
    assert first["count"] == 51
    assert len(first["results"]) == 50 and len(second["results"]) == 1
    assert [x["id"] for x in first["results"] + second["results"]] == [
        x.pk for x in reversed(events)
    ]
    assert first["next"] and second["previous"] and second["next"] is None
    assert client.get("/api/audit-events/", {"page": 3}).status_code == 404
