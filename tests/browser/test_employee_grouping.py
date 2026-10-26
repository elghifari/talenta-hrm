import json
from pathlib import Path

import pytest
from audit.models import AuditEvent
from employees.models import Employee, EmployeeAssignment
from organization.models import Branch, Division, UnitAccess
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def add_choice(page, label, name, owner=None):
    if owner:
        page.get_by_role("button", name=f"Edit cabang {owner}", exact=True).click()
        page.get_by_role("button", name="Tambah divisi", exact=True).click()
        page.get_by_label("Nama divisi 1", exact=True).fill(name)
        page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    else:
        page.get_by_role("button", name=f"Tambah {label}", exact=True).click()
        page.get_by_label(f"Nama {label}", exact=True).fill(name)
        page.get_by_role("button", name=f"Simpan {label}", exact=True).click()
    panel = page.get_by_role("region", name="Tabel cabang dan divisi", exact=True)
    expect(panel.get_by_text(name, exact=True)).to_be_visible()
    return panel


def assert_table_presentation(page, captures):
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.mouse.move(0, 0)
    measured = page.evaluate("""() => {
      const style = selector => getComputedStyle(document.querySelector(selector));
      const center = element => {
        const node = [...element.childNodes].find(item =>
          item.nodeType === 3 && item.textContent.trim());
        const range = document.createRange(); range.selectNodeContents(node);
        const box = range.getBoundingClientRect(); return box.y + box.height / 2;
      };
      const alignment = [...document.querySelectorAll('.employee-data-row')].map(row => {
        const centers = [...row.cells].map(cell => center(cell.querySelector('a') || cell));
        return Math.max(...centers) - Math.min(...centers);
      });
      const countGaps = [...document.querySelectorAll('.group-count')].map(count => {
        const range = document.createRange(); range.selectNodeContents(count.parentNode.firstChild);
        return count.getBoundingClientRect().left - range.getBoundingClientRect().right;
      });
      const select = style('#employee-grouping');
      return {
        header: style('.employee-table th').backgroundColor,
        headerText: style('.employee-table th').color,
        branch: style('.employee-group.branch td').backgroundColor,
        division: style('.employee-group.division td').backgroundColor,
        appearance: select.appearance, arrowPosition: select.backgroundPositionX,
        arrowSize: select.backgroundSize, selectPadding: parseFloat(select.paddingRight),
        linkHeight: document.querySelector('.employee-data-row a').getBoundingClientRect().height,
        alignment, countGaps,
        hintsPresent: /nol di depan|disimpan sebagai teks/i.test(document.body.innerText)
      };
    }""")
    assert measured["header"] == "rgb(22, 48, 73)"
    assert measured["headerText"] == "rgb(255, 255, 255)"
    assert measured["branch"] == "rgb(220, 232, 244)"
    assert measured["division"] == "rgb(238, 244, 250)"
    assert measured["appearance"] == "none" and "14px" in measured["arrowPosition"]
    assert measured["selectPadding"] >= 42 and measured["arrowSize"] == "12px 12px"
    assert measured["linkHeight"] >= 44
    assert measured["alignment"] and max(measured["alignment"]) <= 2, measured
    assert measured["countGaps"] and all(-1 <= gap <= 8 for gap in measured["countGaps"]), measured
    assert not measured["hintsPresent"]
    assert page.locator("label[for='employee-grouping']").count() == 0
    page.emulate_media(forced_colors="active")
    assert (
        page.get_by_label("Grouping", exact=True).evaluate(
            "element => getComputedStyle(element).appearance"
        )
        == "auto"
    )
    page.emulate_media(forced_colors="none")
    (captures / "table-presentation.json").write_text(
        json.dumps(measured, indent=2), encoding="utf-8"
    )


def test_hr_manages_assigns_filters_and_manager_scope_stays_intact(
    page, login, logout, db_call, live_server, synthetic_data
):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page)
    page.get_by_role("link", name="Cabang & Divisi", exact=True).click()
    branch_panel = add_choice(page, "cabang", "Cabang Sintetis A")
    add_choice(page, "divisi", "Pelayanan Sintetis", owner="Cabang Sintetis A")
    branch_panel.get_by_role("button", name="Edit cabang Cabang Sintetis A", exact=True).click()
    page.get_by_label("Nama cabang", exact=True).fill("Cabang Sintetis Baru")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(branch_panel.get_by_text("Cabang Sintetis Baru", exact=True)).to_be_visible()
    page.get_by_role("link", name="Data pegawai", exact=True).click()
    page.get_by_role("link", name="Pegawai Contoh Own", exact=True).click()
    page.get_by_role("link", name="Ubah data", exact=True).click()
    page.get_by_label("Cabang", exact=True).select_option(label="Cabang Sintetis Baru")
    page.get_by_label("Divisi", exact=True).select_option(label="Pelayanan Sintetis")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Contoh Own", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_text("Cabang Sintetis Baru", exact=True)).to_be_visible()
    assert (
        db_call(lambda: Employee.objects.get(pk=synthetic_data.records["own"].pk).branch.name)
        == "Cabang Sintetis Baru"
    )
    assert db_call(lambda: EmployeeAssignment.objects.count()) == 5
    assert db_call(lambda: UnitAccess.objects.count()) == 2
    csrf = page.request.get(live_server.url + "/api/auth/csrf/").json()["csrfToken"]
    groups = db_call(
        lambda: {"branch": str(Branch.objects.get().pk), "division": str(Division.objects.get().pk)}
    )
    response = page.request.patch(
        live_server.url + f"/api/employees/{synthetic_data.records['outside'].pk}/",
        data=groups,
        headers={"X-CSRFToken": csrf},
    )
    assert response.status == 200
    page.get_by_role("navigation", name="Breadcrumb").get_by_role(
        "link", name="Data pegawai", exact=True
    ).click()
    branch_id = groups["branch"]
    page.get_by_label("Cabang", exact=True).select_option(branch_id)
    expect(page.locator(".employee-data-row")).to_have_count(2)
    expect(page.get_by_role("link", name="Pegawai Contoh Outside", exact=True)).to_be_visible()
    page.get_by_label("Grouping", exact=True).select_option("none")
    expect(page.get_by_label("Grouping", exact=True).locator("option:checked")).to_have_text("All")
    expect(page.get_by_role("columnheader", name="Cabang", exact=True)).to_be_visible()
    sort = page.get_by_label("Sort by", exact=True)
    sort.select_option("full_name")
    ordered = page.locator(".employee-data-row a").all_text_contents()
    assert ordered == sorted(ordered)
    page.get_by_role("button", name="Asc: urutan menaik", exact=True).click()
    assert page.locator(".employee-data-row a").all_text_contents() == list(reversed(ordered))
    page.get_by_role("button", name="Desc: urutan menurun", exact=True).click()
    sort.select_option("employee_code")
    assert page.locator(".employee-viewbar [role='status']").count() == 0
    page.get_by_label("Cari pegawai", exact=True).fill("no-match")
    expect(
        page.get_by_role("heading", name="Tidak ada pegawai yang cocok", exact=True)
    ).to_be_visible()
    page.get_by_role("region", name="Hasil pencarian kosong", exact=True).get_by_role(
        "button", name="Reset filter", exact=True
    ).click()
    page.get_by_label("Grouping", exact=True).select_option("both")
    captures = Path(".local/grouping-acceptance")
    captures.mkdir(parents=True, exist_ok=True)
    assert_table_presentation(page, captures)
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
        if width in (390, 1440):
            page.screenshot(path=str(captures / f"grouped-table-{width}.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    logout(page)
    login(page, role="manager")
    expect(page.get_by_role("link", name="Pegawai Contoh Own", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Pegawai Contoh Outside", exact=True)).to_have_count(0)
    expect(page.get_by_role("link", name="Cabang & Divisi", exact=True)).to_have_count(0)
    expect(page.get_by_role("columnheader", name="Tanggal lahir", exact=True)).to_have_count(0)
    expect(page.locator(".employee-data-row")).to_have_count(2)
    before = db_call(lambda: AuditEvent.objects.count())
    token = page.request.get(live_server.url + "/api/auth/csrf/").json()["csrfToken"]
    assert page.request.get(live_server.url + "/api/organization/branches/").status == 403
    assert (
        page.request.post(
            live_server.url + "/api/organization/divisions/",
            data={"name": "Denied"},
            headers={"X-CSRFToken": token},
        ).status
        == 403
    )
    assert db_call(lambda: AuditEvent.objects.count()) == before
    assert not errors, errors


def test_uncertain_reference_create_is_not_replayed(page, login, live_server, db_call):
    login(page)
    page.get_by_role("link", name="Cabang & Divisi", exact=True).click()
    posts = []

    def lose_response(route):
        if route.request.method == "POST":
            posts.append(route.request.url)
            assert route.fetch().status == 201
            route.abort("failed")
        else:
            route.continue_()

    page.route("**/api/organization/branches/", lose_response)
    page.get_by_role("button", name="Tambah cabang", exact=True).click()
    page.get_by_label("Nama cabang", exact=True).fill("Cabang Hasil Tidak Pasti")
    page.get_by_role("button", name="Simpan cabang", exact=True).click()
    expect(page.get_by_role("button", name="Periksa daftar terbaru", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Tambah cabang", exact=True)).to_be_disabled()
    page.get_by_role("button", name="Periksa daftar terbaru", exact=True).click()
    expect(
        page.get_by_role("region", name="Tabel cabang dan divisi", exact=True).get_by_text(
            "Cabang Hasil Tidak Pasti", exact=True
        )
    ).to_be_visible()
    assert len(posts) == 1
    assert db_call(lambda: Branch.objects.count()) == 1
    assert db_call(lambda: AuditEvent.objects.filter(action="branch.created").count()) == 1
