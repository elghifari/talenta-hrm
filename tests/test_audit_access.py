import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client


@pytest.mark.django_db
@pytest.mark.parametrize(
    "roles,superuser,active,allowed",
    [
        ([], False, True, False),
        (["HR"], False, True, False),
        (["HR_MANAGER"], False, True, False),
        (["KEPALA_UNIT"], False, True, False),
        (["FINANCE"], False, True, False),
        ([], True, True, False),
        (["HR", "HR_MANAGER"], False, False, False),
        (["HR", "HR_MANAGER"], False, True, True),
    ],
)
def test_audit_requires_active_dual_role(django_user_model, roles, superuser, active, allowed):
    user = django_user_model.objects.create_user(
        email="reader@example.test", is_superuser=superuser, is_staff=superuser, is_active=active
    )
    user.groups.set([Group.objects.get_or_create(name=role)[0] for role in roles])
    client = Client()
    client.force_login(user)
    identity = client.get("/api/auth/me/")
    if active:
        assert identity.json()["capabilities"]["audit_read"] is allowed
    response = client.get("/api/audit-events/")
    assert response.status_code == (200 if allowed else 403)
    if not allowed:
        assert "count" not in response.json() and "results" not in response.json()
    else:
        assert response.json() == {"count": 0, "next": None, "previous": None, "results": []}


@pytest.mark.django_db
def test_anonymous_and_revoked_reader_cannot_obtain_counts(django_user_model):
    client = Client()
    assert client.get("/api/audit-events/").status_code == 403
    user = django_user_model.objects.create_user(email="manager@example.test")
    user.groups.set([Group.objects.get_or_create(name=role)[0] for role in ("HR", "HR_MANAGER")])
    client.force_login(user)
    assert client.get("/api/audit-events/").status_code == 200
    user.groups.remove(Group.objects.get(name="HR_MANAGER"))
    response = client.get("/api/audit-events/")
    assert response.status_code == 403
    assert "count" not in response.json() and "results" not in response.json()


@pytest.mark.django_db
def test_audit_has_no_mutation_or_detail_api(django_user_model):
    user = django_user_model.objects.create_user(email="manager@example.test")
    user.groups.set([Group.objects.get_or_create(name=role)[0] for role in ("HR", "HR_MANAGER")])
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    csrf = client.get("/api/auth/csrf/").json()["csrfToken"]
    for method in ("post", "patch", "put", "delete"):
        response = getattr(client, method)(
            "/api/audit-events/", data="{}", content_type="application/json", HTTP_X_CSRFTOKEN=csrf
        )
        assert response.status_code == 405
    assert client.get("/api/audit-events/1/").status_code == 404
    assert AuditEvent.objects.count() == 0
