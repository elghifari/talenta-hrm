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


@pytest.mark.django_db
def test_logout_view_204_has_no_body_before_http_transport(django_user_model):
    from accounts.views import SessionLogoutView
    from django.contrib.auth import login
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.test import RequestFactory

    user = django_user_model.objects.create_user(email="synthetic-http@example.test")
    request = RequestFactory().post("/api/auth/logout/")
    SessionMiddleware(lambda request: None).process_request(request)
    login(request, user)
    request.user = user
    response = SessionLogoutView().post(request)
    assert response.status_code == 204
    assert response.content == b""
