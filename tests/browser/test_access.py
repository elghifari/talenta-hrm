import pytest
from audit.models import AuditEvent
from employees.models import Employee
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def test_manager_direct_api_denials_and_explicit_unit_scope(
    page, live_server, login, synthetic_data, db_call
):
    login(page, "manager")
    expect(page.get_by_role("link", name="Pegawai Contoh Own", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Pegawai Contoh Second", exact=True)).to_be_visible()
    assert page.get_by_role("link", name="Tambah pegawai", exact=True).count() == 0
    for key in ["outside", "old", "future", "unassigned"]:
        assert (
            page.get_by_role("link", name=synthetic_data.records[key].full_name, exact=True).count()
            == 0
        )
    request = page.context.request
    token = request.get(live_server.url + "/api/auth/csrf/").json()["csrfToken"]
    headers = {"X-CSRFToken": token}
    own = synthetic_data.records["own"]
    before = db_call(lambda: Employee.objects.count())
    assert (
        request.post(
            live_server.url + "/api/employees/",
            data={"employee_code": "0099", "full_name": "Synthetic Denied"},
            headers=headers,
        ).status
        == 403
    )
    assert (
        request.patch(
            live_server.url + f"/api/employees/{own.pk}/",
            data={"full_name": "Synthetic Denied"},
            headers=headers,
        ).status
        == 403
    )
    db_call(own.refresh_from_db)
    assert own.full_name == "Pegawai Contoh Own"
    assert db_call(lambda: Employee.objects.count()) == before
    assert not db_call(lambda: AuditEvent.objects.exists())
    outside = synthetic_data.records["outside"]
    assert request.get(live_server.url + f"/api/employees/{outside.pk}/").status == 404
    assert request.get(live_server.url + f"/api/employees/{own.pk}/compensation/").status == 403
    page.goto(live_server.url + f"/employees/{outside.pk}")
    expect(
        page.get_by_role("heading", name="Data pegawai tidak tersedia", exact=True)
    ).to_be_visible()
    page.goto(live_server.url + f"/employees/{own.pk}/edit")
    expect(page.get_by_role("heading", name="Akses tidak tersedia", exact=True)).to_be_visible()
    assert page.get_by_label("Nama lengkap", exact=True).count() == 0


def test_finance_cannot_read_employee_ui_or_gain_write_access(page, live_server, login):
    login(page, "finance")
    expect(page.get_by_role("heading", name="Akses tidak tersedia", exact=True)).to_be_visible()
    assert page.context.request.get(live_server.url + "/api/employees/").status == 403


def test_hr_write_without_csrf_is_denied(page, live_server, login, db_call):
    login(page)
    response = page.context.request.post(
        live_server.url + "/api/employees/",
        data={"employee_code": "0099", "full_name": "Synthetic Denied"},
    )
    assert response.status == 403
    assert not db_call(lambda: Employee.objects.filter(employee_code="0099").exists())
    assert not db_call(lambda: AuditEvent.objects.exists())
