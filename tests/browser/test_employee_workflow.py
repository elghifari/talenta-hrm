import pytest
from audit.models import AuditEvent
from employees.models import Employee
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def test_hr_create_edit_reload_validation_and_audits(page, live_server, login, db_call):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    account = login(page)
    page.get_by_role("link", name="Tambah pegawai", exact=True).click()
    page.get_by_role("button", name="Simpan pegawai", exact=True).click()
    expect(page.get_by_text("Kode pegawai wajib diisi.")).to_be_visible()
    page.get_by_label("Kode pegawai", exact=True).fill("0001")
    page.get_by_label("Nama lengkap", exact=True).fill("Pegawai Contoh Browser")
    page.get_by_role("button", name="Simpan pegawai", exact=True).click()
    expect(page.locator("#code-error")).not_to_be_empty()
    assert not db_call(lambda: AuditEvent.objects.exists())
    page.get_by_label("Kode pegawai", exact=True).fill("0099")
    page.get_by_role("button", name="Simpan pegawai", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Contoh Browser", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_text("0099", exact=True)).to_be_visible()
    employee = db_call(lambda: Employee.objects.get(employee_code="0099"))
    assert (
        db_call(
            lambda: AuditEvent.objects.filter(
                actor=account.user, action="employee.created", target_id=employee.pk
            ).count()
        )
        == 1
    )
    page.get_by_role("link", name="Ubah data", exact=True).click()
    expect(page.get_by_role("button", name="Simpan perubahan", exact=True)).to_be_disabled()
    page.get_by_label("Nama lengkap", exact=True).fill("Pegawai Contoh Diperbarui")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(
        page.get_by_role("heading", name="Pegawai Contoh Diperbarui", exact=True)
    ).to_be_visible()
    page.reload()
    expect(
        page.get_by_role("heading", name="Pegawai Contoh Diperbarui", exact=True)
    ).to_be_visible()
    db_call(employee.refresh_from_db)
    assert employee.full_name == "Pegawai Contoh Diperbarui"
    assert (
        db_call(
            lambda: AuditEvent.objects.filter(
                actor=account.user, action="employee.updated", target_id=employee.pk
            ).count()
        )
        == 1
    )
    assert not errors


def test_dirty_navigation_and_phone_menu(page, login):
    login(page)
    page.get_by_role("link", name="Tambah pegawai", exact=True).click()
    page.get_by_label("Nama lengkap", exact=True).fill("Pegawai Contoh Draft")
    page.get_by_role("button", name="Batal", exact=True).click()
    expect(page.get_by_role("alertdialog")).to_be_visible()
    page.get_by_role("button", name="Tetap mengedit", exact=True).click()
    expect(page.get_by_label("Nama lengkap", exact=True)).to_have_value("Pegawai Contoh Draft")
    page.get_by_role("button", name="Batal", exact=True).click()
    page.get_by_role("button", name="Tinggalkan halaman", exact=True).click()
    expect(page.get_by_role("heading", name="Data pegawai", exact=True)).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_role("button", name="Menu", exact=True).click()
    expect(page.get_by_role("link", name="Personnel", exact=True)).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("button", name="Menu", exact=True)).to_be_focused()
    for width in [360, 390, 768, 1280, 1440]:
        page.set_viewport_size({"width": width, "height": 900})
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
