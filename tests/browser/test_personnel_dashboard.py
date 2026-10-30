from datetime import timedelta
from pathlib import Path

import pytest
from audit.models import AuditEvent
from django.utils import timezone
from employees.models import Employee, EmployeeAssignment
from organization.models import Branch, Division, UnitAccess
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def test_dashboard_dialog_and_populated_division_deletion(
    page, login, logout, db_call, synthetic_data
):
    def prepare():
        branch = Branch.objects.create(name="Synthetic Branch")
        division = Division.objects.create(name="Synthetic Division", branch=branch)
        employee = synthetic_data.records["own"]
        Employee.objects.filter(pk=employee.pk).update(
            branch=branch,
            division=division,
            contract_expiry=timezone.localdate() + timedelta(days=7),
        )
        return str(branch.pk), str(division.pk), str(employee.pk)

    branch_id, division_id, employee_id = db_call(prepare)
    login(page)
    modules = page.get_by_role("navigation", name="Modul", exact=True)
    modules.get_by_role("link", name="Ringkasan", exact=True).click()
    expect(page.get_by_role("heading", name="Personnel", exact=True)).to_be_visible()
    expect(page.get_by_role("navigation", name="Breadcrumb")).to_have_count(0)
    expect(
        page.locator(".personnel-metric").filter(has_text="Karyawan").locator("strong")
    ).to_have_text("6")
    expect(
        page.locator(".personnel-metric")
        .filter(has_text="Kontrak segera berakhir")
        .locator("strong")
    ).to_have_text("1")
    expect(page.get_by_role("table").get_by_role("link", name="Pegawai Contoh Own")).to_be_visible()
    modules.get_by_role("link", name="Cabang & Divisi", exact=True).click()
    branch_row = page.locator(".organization-branch")
    division_row = page.locator(".organization-division")
    assert branch_row.bounding_box()["height"] < 72
    assert branch_row.bounding_box()["height"] > division_row.bounding_box()["height"]
    expect(division_row.get_by_role("button")).to_have_count(0)
    branch_row.hover()
    assert (
        branch_row.locator("td").evaluate_all(
            "cells => new Set(cells.map(cell => getComputedStyle(cell).backgroundColor)).size"
        )
        == 1
    )
    page.locator(".organization-toggle").click()
    assert (
        branch_row.locator("td").first.evaluate(
            "cell => parseFloat(getComputedStyle(cell).borderBottomWidth)"
        )
        >= 1
    )
    page.locator(".organization-toggle").click()
    edit = page.get_by_role("button", name="Edit cabang Synthetic Branch", exact=True)
    edit.click()
    dialog = page.get_by_role("dialog", name="Edit cabang", exact=True)
    expect(dialog.get_by_label("Nama cabang", exact=True)).to_be_focused()
    captures = Path(".local/personnel-acceptance")
    captures.mkdir(parents=True, exist_ok=True)
    for width in (1440, 390):
        page.set_viewport_size({"width": width, "height": 850})
        assert dialog.bounding_box()["width"] <= width
        page.screenshot(path=str(captures / f"branch-dialog-{width}.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    dialog.get_by_role("button", name="Hapus divisi Synthetic Division", exact=True).click()
    expect(
        page.get_by_text(
            "1 karyawan akan tetap di cabang masing-masing, dengan Divisi dikosongkan. "
            "Data karyawan tidak dihapus.",
            exact=True,
        )
    ).to_be_visible()
    confirm = page.get_by_role("button", name="Hapus divisi", exact=True)
    assert (
        confirm.evaluate("element => getComputedStyle(element).backgroundColor")
        == "rgb(180, 35, 24)"
    )
    page.get_by_role("button", name="Batal", exact=True).click()
    assert db_call(lambda: Division.objects.filter(pk=division_id).exists())
    page.get_by_role("button", name="Hapus divisi Synthetic Division", exact=True).click()
    expect(confirm).to_be_enabled()
    confirm.click()
    page.screenshot(path=str(captures / "after-delete-confirmation.png"), full_page=True)
    expect(page.get_by_role("heading", name="Akan dihapus", exact=True)).to_be_visible()
    assert db_call(lambda: Employee.objects.get(pk=employee_id).division_id) is not None
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    page.reload()
    expect(page.locator(".organization-division")).to_have_count(0)
    assert not db_call(lambda: Division.objects.filter(pk=division_id).exists())
    assert db_call(lambda: str(Employee.objects.get(pk=employee_id).branch_id)) == branch_id
    assert db_call(lambda: Employee.objects.get(pk=employee_id).division_id) is None
    assert db_call(lambda: Employee.objects.count()) == 6
    assert db_call(lambda: EmployeeAssignment.objects.count()) == 5
    assert db_call(lambda: UnitAccess.objects.count()) == 2
    assert (
        db_call(
            lambda: AuditEvent.objects.filter(
                action="division.deleted", target_id=division_id
            ).count()
        )
        == 1
    )
    logout(page)
    login(page, role="manager")
    modules.get_by_role("link", name="Ringkasan", exact=True).click()
    expect(page.locator(".personnel-metric")).to_have_count(1)
    expect(page.locator(".personnel-metric strong")).to_have_text("2")
    expect(page.get_by_role("table")).to_have_count(0)
