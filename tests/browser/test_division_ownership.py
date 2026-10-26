from pathlib import Path

import pytest
from audit.models import AuditEvent
from employees.models import Employee
from organization.models import Division
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def test_same_named_owned_divisions_follow_branch_selection_and_persist(
    page, login, db_call, live_server, synthetic_data
):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page)
    expect(page.get_by_role("link", name="Batch Upload", exact=True)).to_be_visible()
    page.get_by_role("link", name="Cabang & Divisi", exact=True).click()
    for name in ("KURI", "Sekolah"):
        page.get_by_role("button", name="Tambah cabang", exact=True).click()
        page.get_by_label("Nama cabang", exact=True).fill(name)
        page.get_by_role("button", name="Simpan cabang", exact=True).click()
        expect(
            page.get_by_role("region", name="Tabel cabang dan divisi", exact=True).get_by_text(
                name, exact=True
            )
        ).to_be_visible()
    for branch in ("KURI", "Sekolah"):
        page.get_by_role("button", name=f"Edit cabang {branch}", exact=True).click()
        page.get_by_role("button", name="Tambah divisi", exact=True).click()
        page.get_by_label("Nama divisi 1", exact=True).fill("Marketing")
        page.get_by_role("button", name="Simpan perubahan", exact=True).click()
        expect(page.get_by_role("dialog")).to_have_count(0)
    toggle = page.locator(".organization-toggle").filter(has_text="KURI")
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "false")
    expect(page.locator(".organization-division")).to_have_count(1)
    toggle.press("Enter")
    expect(toggle).to_have_attribute("aria-expanded", "true")
    expect(page.locator(".organization-division")).to_have_count(2)
    page.get_by_role("button", name="Edit cabang KURI", exact=True).click()
    page.get_by_label("Nama divisi 1", exact=True).fill("Marketing KURI")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    page.get_by_role("button", name="Edit cabang KURI", exact=True).click()
    page.get_by_label("Nama divisi 1", exact=True).fill("Marketing")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    assert db_call(lambda: set(Division.objects.values_list("name", "branch__name"))) == {
        ("Marketing", "KURI"),
        ("Marketing", "Sekolah"),
    }
    before = db_call(lambda: AuditEvent.objects.count())
    page.get_by_role("button", name="Edit cabang Sekolah", exact=True).click()
    page.get_by_role("button", name="Tambah divisi", exact=True).click()
    page.get_by_label("Nama divisi 2", exact=True).fill("marketing")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("alert")).to_have_text("Nama divisi kosong atau duplikat.")
    assert db_call(lambda: AuditEvent.objects.count()) == before
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Batal", exact=True).click()
    captures = Path(".local/division-ownership-acceptance")
    captures.mkdir(parents=True, exist_ok=True)
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
        if width in (390, 1440):
            page.screenshot(
                path=str(captures / f"ownership-management-{width}.png"), full_page=True
            )
    page.set_viewport_size({"width": 1440, "height": 1000})
    choices = db_call(
        lambda: {
            item.branch.name: {"branch": str(item.branch_id), "division": str(item.pk)}
            for item in Division.objects.select_related("branch")
        }
    )
    page.get_by_role("link", name="Data pegawai", exact=True).click()
    page.get_by_role("link", name="Pegawai Contoh Own", exact=True).click()
    page.get_by_role("link", name="Ubah data", exact=True).click()
    division = page.get_by_label("Divisi", exact=True)
    expect(division).to_be_disabled()
    page.get_by_label("Cabang", exact=True).select_option(label="KURI")
    expect(division.get_by_role("option")).to_have_count(2)
    assert division.get_by_role("option").evaluate_all(
        "options => options.map(option => option.value)"
    ) == ["", choices["KURI"]["division"]]
    division.select_option(label="Marketing")
    page.get_by_label("Cabang", exact=True).select_option(label="Sekolah")
    expect(division).to_have_value("")
    assert division.get_by_role("option").evaluate_all(
        "options => options.map(option => option.value)"
    ) == ["", choices["Sekolah"]["division"]]
    division.select_option(label="Marketing")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Contoh Own", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_text("Sekolah", exact=True)).to_be_visible()
    expect(page.get_by_text("Marketing", exact=True)).to_be_visible()
    own = synthetic_data.records["own"].pk
    assert db_call(
        lambda: (
            str(Employee.objects.get(pk=own).branch_id),
            str(Employee.objects.get(pk=own).division_id),
        )
    ) == (choices["Sekolah"]["branch"], choices["Sekolah"]["division"])
    token = page.request.get(live_server.url + "/api/auth/csrf/").json()["csrfToken"]
    before = db_call(lambda: AuditEvent.objects.count())
    rejected = page.request.patch(
        live_server.url + f"/api/employees/{own}/",
        data={"branch": choices["KURI"]["branch"]},
        headers={"X-CSRFToken": token},
    )
    assert rejected.status == 400
    assert db_call(lambda: AuditEvent.objects.count()) == before
    outside = synthetic_data.records["outside"].pk
    assert (
        page.request.patch(
            live_server.url + f"/api/employees/{outside}/",
            data=choices["KURI"],
            headers={"X-CSRFToken": token},
        ).status
        == 200
    )
    page.get_by_role("navigation", name="Breadcrumb").get_by_role(
        "link", name="Data pegawai", exact=True
    ).click()
    division_filter = page.get_by_label("Divisi", exact=True)
    expect(
        division_filter.get_by_role("option", name="Marketing (KURI)", exact=True)
    ).to_have_attribute("value", choices["KURI"]["division"])
    expect(
        division_filter.get_by_role("option", name="Marketing (Sekolah)", exact=True)
    ).to_have_attribute("value", choices["Sekolah"]["division"])
    page.get_by_label("Grouping", exact=True).select_option("division")
    expect(
        page.get_by_role("button", name="Marketing (KURI) · 1 karyawan", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_role("button", name="Marketing (Sekolah) · 1 karyawan", exact=True)
    ).to_be_visible()
    division_filter.select_option(choices["KURI"]["division"])
    expect(page.get_by_role("link", name="Pegawai Contoh Own", exact=True)).to_have_count(0)
    expect(page.get_by_role("link", name="Pegawai Contoh Outside", exact=True)).to_be_visible()
    assert not errors, errors
