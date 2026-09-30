import json
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

import pytest
from django.contrib.auth.models import Group


@pytest.mark.django_db(transaction=True)
def test_live_http_session_and_employee_workflow(live_server, django_user_model):
    user = django_user_model.objects.create_user(
        email="smoke@example.test", password="Synthetic-test-password-42"
    )
    user.groups.add(Group.objects.get_or_create(name="HR")[0])
    opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(path, method="GET", data=None, token=None, form=False):
        headers = {}
        body = None
        if data is not None:
            body = (urlencode(data) if form else json.dumps(data)).encode()
            headers["Content-Type"] = (
                "application/x-www-form-urlencoded" if form else "application/json"
            )
        if token:
            headers["X-CSRFToken"] = token
        req = Request(live_server.url + path, data=body, headers=headers, method=method)
        try:
            response = opener.open(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            payload = (
                json.loads(raw) if raw and "json" in response.headers.get_content_type() else None
            )
            return response.status, payload

    assert request("/api/health/") == (200, {"status": "ok"})
    assert request("/api/employees/")[0] == 403
    token = request("/api/auth/csrf/")[1]["csrfToken"]
    assert (
        request(
            "/api/auth/login/",
            "POST",
            {"username": "smoke@example.test", "password": "Synthetic-test-password-42"},
            token,
            form=True,
        )[0]
        == 200
    )
    assert request("/api/auth/me/")[1]["email"] == "smoke@example.test"
    token = request("/api/auth/csrf/")[1]["csrfToken"]
    status, payload = request(
        "/api/employees/",
        "POST",
        {"employee_code": "0007", "full_name": "Synthetic Live Employee"},
        token,
    )
    assert status == 201
    detail = f"/api/employees/{payload['id']}/"
    assert request(detail)[1]["employee_code"] == "0007"
    assert request(detail, "PATCH", {"full_name": "Synthetic Corrected"}, token)[0] == 200
    assert request(detail)[1]["full_name"] == "Synthetic Corrected"
    assert request("/api/auth/logout/", "POST", {})[0] == 403
    assert request("/api/auth/logout/", "POST", {}, token)[0] == 204
    assert request("/api/auth/me/")[0] == 403
