import pytest
from django.test import Client


@pytest.mark.django_db
@pytest.mark.parametrize("active", [True, False])
def test_invalid_login_returns_generic_json(django_user_model, active):
    django_user_model.objects.create_user(
        email="hr@example.test", password="Synthetic-test-password-42", is_active=active
    )
    response = Client().post(
        "/api/auth/login/", {"username": "hr@example.test", "password": "wrong-password"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid email or password"}


@pytest.mark.django_db
def test_login_rejects_missing_csrf(django_user_model):
    django_user_model.objects.create_user(
        email="hr@example.test", password="Synthetic-test-password-42"
    )
    response = Client(enforce_csrf_checks=True).post(
        "/api/auth/login/",
        {"username": "hr@example.test", "password": "Synthetic-test-password-42"},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_anonymous_session_cannot_read_account():
    assert Client().get("/api/auth/me/").status_code == 403
