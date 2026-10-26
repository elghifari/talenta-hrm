from pathlib import Path

import pytest
from audit.models import AuditEvent
from employees.models import Employee
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)
VALUES = {
    "date_of_birth": "1996-04-12",
    "job_title": "Synthetic Therapist",
    "level": "Level 2",
    "start_date": "2024-01-01",
    "contract_expiry": "2027-12-31",
}
LABELS = {
    "date_of_birth": "Tanggal lahir",
    "job_title": "Jabatan",
    "level": "Level",
    "start_date": "Tanggal masuk",
    "contract_expiry": "Kontrak berakhir",
}


def test_profile_edit_validation_clear_and_breadcrumb_navigation(
    page, login, db_call, synthetic_data
):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page)
    page.get_by_role("link", name="Pegawai Contoh Own", exact=True).click()
    page.get_by_role("link", name="Ubah data", exact=True).click()
    expect(
        page.get_by_role("navigation", name="Breadcrumb").get_by_role(
            "link", name="Detail pegawai", exact=True
        )
    ).to_be_visible()
    for key, label in LABELS.items():
        page.get_by_label(label, exact=True).fill(VALUES[key])
    captures = Path(".local/profile-ui-acceptance")
    captures.mkdir(parents=True, exist_ok=True)
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
        if width in (390, 1440):
            page.screenshot(path=str(captures / f"employee-edit-{width}.png"), full_page=True)
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Contoh Own", exact=True)).to_be_visible()
    page.reload()
    for value in VALUES.values():
        expect(page.get_by_text(value, exact=True)).to_be_visible()
    pk = synthetic_data.records["own"].pk
    persisted = db_call(lambda: Employee.objects.values(*VALUES).get(pk=pk))
    assert {key: str(value) for key, value in persisted.items()} == VALUES
    assert (
        db_call(lambda: AuditEvent.objects.filter(action="employee.updated", target_id=pk).count())
        == 1
    )
    page.get_by_role("link", name="Ubah data", exact=True).click()
    page.get_by_label("Kontrak berakhir", exact=True).fill("2023-12-31")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_text("Kontrak berakhir sebelum tanggal masuk.", exact=True)).to_be_visible()
    expect(page.get_by_label("Kontrak berakhir", exact=True)).to_be_focused()
    assert (
        db_call(lambda: AuditEvent.objects.filter(action="employee.updated", target_id=pk).count())
        == 1
    )
    for label in LABELS.values():
        page.get_by_label(label, exact=True).clear()
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("heading", name="Pegawai Contoh Own", exact=True)).to_be_visible()
    assert db_call(lambda: Employee.objects.values(*VALUES).get(pk=pk)) == {
        "date_of_birth": None,
        "job_title": "",
        "level": "",
        "start_date": None,
        "contract_expiry": None,
    }
    page.get_by_role("navigation", name="Breadcrumb").get_by_role(
        "link", name="Data pegawai", exact=True
    ).click()
    expect(page.get_by_role("heading", name="Data pegawai", exact=True)).to_be_visible()
    assert not errors, errors
