import pytest
from django.test import Client


@pytest.mark.django_db
def test_email_login_creates_a_csrf_protected_session(django_user_model):
    django_user_model.objects.create_user(
        email="hr@example.test", password="Synthetic-test-password-42"
    )
    client = Client(enforce_csrf_checks=True)
    response = client.get("/api/auth/csrf/")
    assert response.status_code == 200
    response = client.post(
        "/api/auth/login/",
        {"username": "hr@example.test", "password": "Synthetic-test-password-42"},
        HTTP_X_CSRFTOKEN=response.json()["csrfToken"],
    )
    assert response.status_code == 200
    assert client.get("/api/auth/me/").json()["email"] == "hr@example.test"
