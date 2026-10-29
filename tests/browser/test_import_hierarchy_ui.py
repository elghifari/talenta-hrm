from pathlib import Path

import pytest
from audit.models import AuditEvent
from employees.models import Employee, EmployeeAssignment
from organization.models import Branch, Division
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def prepare_hierarchy():
    first = Branch.objects.create(name="Cabang Lama")
    second = Branch.objects.create(name="Cabang Baru")
    old = Division.objects.create(branch=first, name="Pelayanan")
    new = Division.objects.create(branch=second, name="Pelayanan")
    Employee.objects.filter(employee_code="0001").update(branch=first, division=old)
    return str(first.pk), str(second.pk), str(new.pk)


def preview(page, login, content):
    login(page)
    page.get_by_role("link", name="Batch Upload", exact=True).click()
    with page.expect_download() as download:
        page.get_by_role("link", name="Download template CSV", exact=True).click()
    headers = Path(download.value.path()).read_text(encoding="utf-8-sig").splitlines()[0]
    assert headers.split(",")[2:4] == ["Cabang", "Divisi"]
    page.get_by_label("File CSV", exact=True).set_input_files(
        {"name": "hierarki.csv", "mimeType": "text/csv", "buffer": content.encode()}
    )
    with page.expect_response(lambda response: "/api/employees/import-preview/" in response.url):
        page.get_by_role("button", name="Pratinjau CSV", exact=True).click()
    expect(page.get_by_role("heading", name="Pratinjau Batch Upload", exact=True)).to_be_visible()


def test_csv_hierarchy_review_persistence_and_responsive_layout(page, login, db_call):
    first, second, division = db_call(prepare_hierarchy)
    assignments = db_call(lambda: list(EmployeeAssignment.objects.order_by("pk").values()))
    preview(
        page,
        login,
        "ID Karyawan,Nama Lengkap,Cabang,Divisi\n"
        "0001,Pegawai Contoh Own,Cabang Baru,Pelayanan\n"
        "0007,Karyawan Hierarki,Cabang Baru,Pelayanan\n"
        "0008,Karyawan Cabang,Cabang Lama,\n",
    )
    expect(page.locator(".import-marker")).to_have_text(["Upd", "New", "New"])
    row = page.locator(".import-line").first
    row.locator("summary").click()
    expect(row.get_by_role("cell", name="Cabang Lama", exact=True)).to_be_visible()
    expect(row.get_by_role("cell", name="Cabang Baru", exact=True)).to_be_visible()
    expect(row.get_by_role("rowheader", name="Divisi", exact=True)).to_be_visible()
    expect(page.get_by_text(second, exact=True)).to_have_count(0)
    captures = Path(".local/import-hierarchy-acceptance")
    captures.mkdir(parents=True, exist_ok=True)
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.screenshot(path=str(captures / f"hierarchy-{width}.png"), full_page=True)
    assert db_call(lambda: Employee.objects.count()) == 6
    assert db_call(lambda: AuditEvent.objects.count()) == 0
    page.get_by_role("button", name="Konfirmasi upload", exact=True).click()
    expect(page.get_by_text("Data pegawai berhasil diimpor.", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_text("Data pegawai berhasil diimpor.", exact=True)).to_be_visible()
    for code in ("0001", "0007"):
        pair = db_call(
            lambda: Employee.objects.values_list("branch_id", "division_id").get(employee_code=code)
        )
        assert tuple(map(str, pair)) == (second, division)
    pair = db_call(
        lambda: Employee.objects.values_list("branch_id", "division_id").get(employee_code="0008")
    )
    assert (str(pair[0]), pair[1]) == (first, None)
    assert db_call(lambda: Employee.objects.count()) == 8
    assert db_call(lambda: AuditEvent.objects.count()) == 3
    assert db_call(lambda: list(EmployeeAssignment.objects.order_by("pk").values())) == assignments


def test_unknown_division_blocks_confirmation_without_creating_organization(page, login, db_call):
    db_call(prepare_hierarchy)
    preview(
        page,
        login,
        "ID Karyawan,Nama Lengkap,Cabang,Divisi\n"
        "0007,Karyawan Hierarki,Cabang Baru,Tidak Terdaftar\n",
    )
    expect(
        page.get_by_text(
            "Divisi: Divisi belum terdaftar di cabang ini. Periksa nama divisi.", exact=True
        )
    ).to_be_visible()
    expect(page.get_by_role("button", name="Konfirmasi upload", exact=True)).to_be_disabled()
    assert db_call(lambda: Employee.objects.count()) == 6
    assert db_call(lambda: AuditEvent.objects.count()) == 0
    assert db_call(lambda: (Branch.objects.count(), Division.objects.count())) == (2, 2)


def test_renamed_division_invalidates_review_without_writing_employees(page, login, db_call):
    _, _, division = db_call(prepare_hierarchy)
    preview(
        page,
        login,
        "ID Karyawan,Nama Lengkap,Cabang,Divisi\n0007,Karyawan Hierarki,Cabang Baru,Pelayanan\n",
    )
    db_call(lambda: Division.objects.filter(pk=division).update(name="Pelayanan Diubah"))
    page.get_by_role("button", name="Konfirmasi upload", exact=True).click()
    expect(
        page.get_by_text(
            "Data berubah sejak pratinjau. Upload ulang CSV untuk melihat perubahan terbaru.",
            exact=True,
        )
    ).to_be_visible()
    expect(page.get_by_role("button", name="Konfirmasi upload", exact=True)).to_be_disabled()
    assert db_call(lambda: Employee.objects.count()) == 6
    assert db_call(lambda: AuditEvent.objects.count()) == 0
