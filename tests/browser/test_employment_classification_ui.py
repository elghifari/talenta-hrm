from pathlib import Path

import pytest
from audit.models import AuditEvent
from employees.models import Employee
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def classification(db_call, code):
    return db_call(
        lambda: Employee.objects.values_list("employment_status", "pkwt_type").get(
            employee_code=code
        )
    )


def test_classification_create_edit_clear_and_restricted_detail(
    page, login, db_call, synthetic_data
):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    account = login(page)
    page.get_by_role("link", name="Tambah pegawai", exact=True).click()
    page.get_by_label("Kode pegawai", exact=True).fill("0099")
    page.get_by_label("Nama lengkap", exact=True).fill("Pegawai Klasifikasi")
    status = page.get_by_label("Status Kepegawaian", exact=True)
    expect(status).to_have_value("")
    status.select_option(label="Kontrak")
    pkwt = page.get_by_label("Tipe PKWT", exact=True)
    page.get_by_role("button", name="Simpan pegawai", exact=True).click()
    expect(pkwt).to_be_focused()
    expect(pkwt).to_have_attribute("aria-invalid", "true")
    assert not db_call(lambda: Employee.objects.filter(employee_code="0099").exists())
    assert db_call(lambda: AuditEvent.objects.count()) == 0
    pkwt.select_option(label="Guru")
    captures = Path(".local/employment-classification-acceptance")
    captures.mkdir(parents=True, exist_ok=True)
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
        page.screenshot(path=str(captures / f"form-{width}.png"), full_page=True)
    page.get_by_role("button", name="Simpan pegawai", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Klasifikasi", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_text("Kontrak", exact=True)).to_be_visible()
    expect(page.get_by_text("Guru", exact=True)).to_be_visible()
    assert classification(db_call, "0099") == ("kontrak", "guru")
    created = db_call(lambda: Employee.objects.get(employee_code="0099"))
    assert (
        db_call(
            lambda: AuditEvent.objects.filter(
                actor=account.user, action="employee.created", target_id=created.pk
            ).count()
        )
        == 1
    )
    page.get_by_role("link", name="Ubah data", exact=True).click()
    expect(page.get_by_role("button", name="Simpan perubahan", exact=True)).to_be_disabled()
    page.get_by_label("Tipe PKWT", exact=True).select_option(label="Klinik Umum")
    page.get_by_role("button", name="Batal", exact=True).click()
    page.get_by_role("button", name="Tetap mengedit", exact=True).click()
    expect(page.get_by_label("Tipe PKWT", exact=True)).to_have_value("klinik_umum")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Klasifikasi", exact=True)).to_be_visible()
    page.reload()
    assert classification(db_call, "0099") == ("kontrak", "klinik_umum")
    page.get_by_role("link", name="Ubah data", exact=True).click()
    page.get_by_label("Status Kepegawaian", exact=True).select_option(label="Permanen")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Klasifikasi", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_text("Permanen", exact=True)).to_be_visible()
    expect(page.get_by_text("Klinik Umum", exact=True)).to_have_count(0)
    assert classification(db_call, "0099") == ("permanen", "")
    assert (
        db_call(
            lambda: AuditEvent.objects.filter(
                actor=account.user, action="employee.updated", target_id=created.pk
            ).count()
        )
        == 2
    )
    own = synthetic_data.records["own"].pk
    db_call(
        lambda: Employee.objects.filter(pk=own).update(
            employment_status="kontrak", pkwt_type="yayasan"
        )
    )
    page.get_by_role("button", name="Keluar", exact=True).click()
    expect(page.get_by_label("Email", exact=True)).to_be_visible()
    login(page, "manager")
    page.get_by_role("link", name="Pegawai Contoh Own", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Contoh Own", exact=True)).to_be_visible()
    expect(page.get_by_text("Status Kepegawaian", exact=True)).to_have_count(0)
    expect(page.get_by_text("Tipe PKWT", exact=True)).to_have_count(0)
    response = page.request.get(page.url.split("/employees/")[0] + f"/api/employees/{own}/")
    assert response.status == 200
    assert "employment_status" not in response.json()
    assert "pkwt_type" not in response.json()
    assert not errors, errors


def test_csv_classification_review_clear_persistence_and_replay(page, login, db_call):
    db_call(
        lambda: Employee.objects.filter(employee_code="0001").update(
            employment_status="kontrak", pkwt_type="guru"
        )
    )
    login(page)
    page.get_by_role("link", name="Batch Upload", exact=True).click()
    with page.expect_download() as download:
        page.get_by_role("link", name="Download template CSV", exact=True).click()
    headers = Path(download.value.path()).read_text(encoding="utf-8-sig").splitlines()[0]
    assert "Status Kepegawaian" in headers.split(",")
    assert "Tipe PKWT" in headers.split(",")
    content = (
        "ID Karyawan,Nama Lengkap,Status Kepegawaian,Tipe PKWT\n"
        "0001,Pegawai Contoh Own,Permanen,\n"
        "0099,Pegawai Kontrak Baru,Kontrak,Klinik Umum\n"
    )
    page.get_by_label("File CSV", exact=True).set_input_files(
        {"name": "klasifikasi.csv", "mimeType": "text/csv", "buffer": content.encode()}
    )
    page.get_by_role("button", name="Pratinjau CSV", exact=True).click()
    expect(page.get_by_role("heading", name="Pratinjau Batch Upload", exact=True)).to_be_visible()
    expect(page.locator(".import-marker")).to_have_text(["Upd", "New"])
    row = page.locator(".import-line").first
    row.locator("summary").click()
    expect(row.get_by_role("rowheader", name="Status Kepegawaian", exact=True)).to_be_visible()
    expect(row.get_by_role("rowheader", name="Tipe PKWT", exact=True)).to_be_visible()
    expect(row.get_by_role("cell", name="Guru", exact=True)).to_be_visible()
    expect(row.get_by_role("cell", name="Permanen", exact=True)).to_be_visible()
    assert classification(db_call, "0001") == ("kontrak", "guru")
    assert db_call(lambda: Employee.objects.count()) == 6
    assert db_call(lambda: AuditEvent.objects.count()) == 0
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
    page.get_by_role("button", name="Konfirmasi upload", exact=True).click()
    expect(page.get_by_text("Data pegawai berhasil diimpor.", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_text("Data pegawai berhasil diimpor.", exact=True)).to_be_visible()
    assert classification(db_call, "0001") == ("permanen", "")
    assert classification(db_call, "0099") == ("kontrak", "klinik_umum")
    assert db_call(lambda: Employee.objects.count()) == 7
    assert db_call(lambda: AuditEvent.objects.count()) == 2
