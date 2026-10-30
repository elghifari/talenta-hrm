import pytest
from django.contrib.auth.models import Group
from django.test import Client


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("roles", "read", "write"),
    [
        (["HR"], True, True),
        (["KEPALA_UNIT"], True, False),
        (["HR", "KEPALA_UNIT"], True, True),
        (["FINANCE"], False, False),
        (["TECHNICAL_ADMIN"], False, False),
        (["INTERN"], False, False),
        ([], False, False),
    ],
)
def test_identity_capabilities_match_employee_permissions(django_user_model, roles, read, write):
    user = django_user_model.objects.create_user(email="synthetic@example.test")
    for role in roles:
        user.groups.add(Group.objects.get_or_create(name=role)[0])
    client = Client()
    client.force_login(user)
    identity = client.get("/api/auth/me/").json()
    assert identity["capabilities"] == {
        "employees_read": read,
        "employees_write": write,
        "audit_read": False,
    }
    assert client.get("/api/employees/").status_code == (200 if read else 403)
    response = client.post(
        "/api/employees/",
        {"employee_code": "0001", "full_name": "Synthetic Employee"},
        content_type="application/json",
    )
    assert response.status_code == (201 if write else 403)


@pytest.mark.django_db
def test_superuser_has_no_implicit_employee_capabilities(django_user_model):
    user = django_user_model.objects.create_superuser(
        email="technical@example.test", password="test"
    )
    client = Client()
    client.force_login(user)
    assert client.get("/api/auth/me/").json()["capabilities"] == {
        "employees_read": False,
        "employees_write": False,
        "audit_read": False,
    }
    assert client.get("/api/employees/").status_code == 403


def test_anonymous_identity_has_no_capability_payload():
    assert Client().get("/api/auth/me/").status_code == 403
