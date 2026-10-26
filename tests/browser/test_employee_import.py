from pathlib import Path

import pytest
from audit.models import AuditEvent
from employees.models import Employee
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

CSV = (
    "Nama Lengkap,ID Karyawan,TTL,Jabatan,Level,Tanggal Masuk,Kontrak Berakhir\n"
    "Pegawai Contoh Own,0001,1996-04-12,Terapis Senior,Level 2,2024-01-01,2027-12-31\n"
    "Karyawan CSV Baru,0007,1998-03-21,Terapis,Level 1,2024-01-01,2027-12-31\n"
    "Pegawai Contoh Second,0003,,,,,\n"
)


def open_preview(page, login):
    login(page)
    page.get_by_role("link", name="Batch Upload", exact=True).click()
    page.get_by_label("File CSV", exact=True).set_input_files(
        {"name": "karyawan.csv", "mimeType": "text/csv", "buffer": CSV.encode()}
    )
    with page.expect_response(
        lambda response: "/api/employees/import-preview/" in response.url
    ) as pending:
        page.get_by_role("button", name="Pratinjau CSV", exact=True).click()
    response = pending.value
    assert response.status == 201, response.text()
    expect(page.get_by_role("button", name="Konfirmasi upload", exact=True)).to_be_enabled()


def test_mixed_csv_review_persistence_and_responsive_layout(page, login, db_call):
    open_preview(page, login)
    assert page.locator(".import-marker").all_text_contents() == ["Upd", "New", "-"]
    expect(page.get_by_text("0001 - Pegawai Contoh Own", exact=True)).to_be_visible()
    expect(page.get_by_text("Pegawai Contoh Outside", exact=True)).to_have_count(0)
    assert db_call(lambda: Employee.objects.count()) == 6
    assert db_call(lambda: AuditEvent.objects.count()) == 0
    row = page.locator(".import-line").first
    row.locator("summary").click()
    expect(row.get_by_role("cell", name="Terapis Senior", exact=True)).to_be_visible()
    row.get_by_role("button", name="Lihat semua kolom", exact=True).click()
    expect(row.get_by_role("rowheader", name="Tanggal lahir", exact=True)).to_be_visible()
    assert page.locator("del,s").count() == 0
    captures = Path(".local/import-acceptance")
    captures.mkdir(parents=True, exist_ok=True)
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert (
            row.locator(".import-marker").bounding_box()["x"]
            < row.locator("details").bounding_box()["x"]
        )
        if width in (390, 1440):
            page.screenshot(path=str(captures / f"preview-{width}.png"), full_page=True)
    page.get_by_role("button", name="Konfirmasi upload", exact=True).click()
    expect(page.get_by_role("heading", name="Batch Upload tersimpan", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_role("heading", name="Batch Upload tersimpan", exact=True)).to_be_visible()
    assert db_call(lambda: Employee.objects.count()) == 7
    assert db_call(lambda: Employee.objects.get(employee_code="0001").job_title) == "Terapis Senior"
    assert (
        db_call(lambda: str(Employee.objects.get(employee_code="0007").date_of_birth))
        == "1998-03-21"
    )
    assert db_call(lambda: AuditEvent.objects.count()) == 2


def test_committed_response_loss_reads_receipt_without_mutation_replay(page, login, db_call):
    open_preview(page, login)
    posts = []

    def lose_response(route):
        posts.append(route.request.url)
        response = route.fetch()
        assert response.status == 200
        route.abort("failed")

    page.route("**/api/employees/imports/*/confirm/", lose_response)
    page.get_by_role("button", name="Konfirmasi upload", exact=True).click()
    expect(page.get_by_role("button", name="Konfirmasi upload", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="Periksa hasil", exact=True)).to_be_visible()
    page.get_by_role("button", name="Periksa hasil", exact=True).click()
    expect(page.get_by_role("heading", name="Batch Upload tersimpan", exact=True)).to_be_visible()
    assert len(posts) == 1
    assert db_call(lambda: Employee.objects.count()) == 7
    assert db_call(lambda: AuditEvent.objects.count()) == 2
