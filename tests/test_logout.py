import pytest
from django.test import Client


@pytest.mark.django_db
def test_logout_ends_session(django_user_model):
    user = django_user_model.objects.create_user(email="hr@example.test")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    token = client.get("/api/auth/csrf/").json()["csrfToken"]
    response = client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 204
    assert client.get("/api/auth/me/").status_code == 403
