from pathlib import Path

import pytest
from audit.models import AuditEvent
from employees.models import Employee, EmployeeAssignment
from organization.models import UnitAccess
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def test_loaded_detail_receives_keyboard_focus(page, login):
    login(page)
    page.get_by_role("link", name="Pegawai Contoh Own", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Contoh Own", exact=True)).to_be_focused()


def test_failed_read_retries_without_losing_session(page, login):
    attempts = 0

    def respond(route):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            route.fulfill(status=503, json={"detail": "Synthetic unavailable"})
        else:
            route.continue_()

    page.route("**/api/employees/", respond)
    login(page)
    expect(page.get_by_role("alert")).to_be_visible()
    page.get_by_role("button", name="Coba lagi", exact=True).click()
    expect(page.get_by_role("link", name="Pegawai Contoh Own", exact=True)).to_be_visible()


def test_real_empty_hr_and_manager_states(page, live_server, login, db_call):
    login(page, "manager")
    db_call(lambda: UnitAccess.objects.all().delete())
    page.reload()
    expect(page.get_by_text("Belum ada pegawai", exact=True)).to_be_visible()
    expect(page.get_by_text("Akses baca saja.", exact=False)).to_be_visible()
    page.get_by_role("button", name="Keluar", exact=True).click()
    login(page)
    db_call(lambda: EmployeeAssignment.objects.all().delete())
    db_call(lambda: Employee.objects.all().delete())
    page.reload()
    expect(page.get_by_role("heading", name="Belum ada pegawai", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Tambah pegawai", exact=True)).to_be_visible()


def test_committed_write_with_lost_response_is_not_repeated(page, login, db_call):
    mutations = 0

    def lose_response(route):
        nonlocal mutations
        if route.request.method == "POST":
            mutations += 1
            response = route.fetch()
            assert response.status == 201
            route.abort()
        else:
            route.continue_()

    login(page)
    page.route("**/api/employees/", lose_response)
    page.get_by_role("link", name="Tambah pegawai", exact=True).click()
    page.get_by_label("Kode pegawai", exact=True).fill("0077")
    page.get_by_label("Nama lengkap", exact=True).fill("Pegawai Contoh Respons Hilang")
    page.get_by_role("button", name="Simpan pegawai", exact=True).click()
    expect(
        page.get_by_text("Hasil penyimpanan belum dapat dipastikan.", exact=False)
    ).to_be_visible()
    expect(page.get_by_role("button", name="Simpan pegawai", exact=True)).to_be_disabled()
    assert db_call(lambda: Employee.objects.filter(employee_code="0077").count()) == 1
    assert db_call(lambda: AuditEvent.objects.filter(action="employee.created").count()) == 1
    assert mutations == 1
    page.get_by_role("link", name="Periksa data tersimpan", exact=True).click()
    page.get_by_role("button", name="Tinggalkan halaman", exact=True).click()
    expect(
        page.get_by_role("link", name="Pegawai Contoh Respons Hilang", exact=True)
    ).to_be_visible()


def test_selected_shell_desktop_phone_and_long_records(page, live_server, login, db_call):
    directory = Path.cwd() / ".local" / "ui-review"
    directory.mkdir(parents=True, exist_ok=True)
    account = login(page)
    page.screenshot(path=str(directory / "desktop.png"), full_page=True)
    page.get_by_role("link", name="Tambah pegawai", exact=True).click()
    page.screenshot(path=str(directory / "create.png"), full_page=True)
    page.get_by_role("button", name="Batal", exact=True).click()
    record = db_call(
        lambda: Employee.objects.create(employee_code="9" * 64, full_name="Synthetic " + "N" * 190)
    )
    page.reload()
    expect(page.get_by_role("link", name=record.full_name, exact=True)).to_be_visible()
    for width in [360, 390, 768, 1280, 1440]:
        page.set_viewport_size({"width": width, "height": 1000})
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(directory / "mobile.png"), full_page=True)
    page.evaluate("document.documentElement.style.fontSize = '200%'")
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    assert account.email in page.locator("body").inner_text()
