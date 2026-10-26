import json
from pathlib import Path

import pytest
from audit.models import AuditEvent
from employees.models import Employee
from organization.models import Branch, Division
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def prepare_divisions(synthetic_data):
    branch = Branch.objects.create(name="Synthetic Settings Branch")
    first = Division.objects.create(name="Synthetic First", branch=branch)
    second = Division.objects.create(name="Synthetic Second", branch=branch)
    Employee.objects.filter(pk=synthetic_data.records["own"].pk).update(
        branch=branch, division=first
    )
    return str(branch.pk), str(first.pk), str(second.pk)


def test_divisi_switches_persist_audit_and_deny_manager_writes(
    page, login, logout, db_call, live_server, synthetic_data
):
    branch_id, first_id, second_id = db_call(lambda: prepare_divisions(synthetic_data))
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page)
    page.get_by_role("link", name="Cabang & Divisi", exact=True).click()
    edit = page.get_by_role("button", name="Edit cabang Synthetic Settings Branch", exact=True)
    edit.click()
    dialog = page.get_by_role("dialog", name="Edit cabang", exact=True)
    first = dialog.get_by_role("group", name="Pengaturan divisi Synthetic First", exact=True)
    kinerja = first.get_by_role("switch", name="Kinerja", exact=True)
    pelimpahan = first.get_by_role("switch", name="Pelimpahan", exact=True)
    expect(kinerja).not_to_be_checked()
    expect(pelimpahan).not_to_be_checked()
    expect(dialog.get_by_role("button", name="Simpan perubahan", exact=True)).to_be_disabled()
    kinerja.focus()
    kinerja.press("Space")
    expect(kinerja).to_be_checked()
    expect(pelimpahan).not_to_be_checked()
    assert kinerja.evaluate("element => getComputedStyle(element).outlineStyle") != "none"
    page.once("dialog", lambda prompt: prompt.dismiss())
    dialog.get_by_role("button", name="Batal", exact=True).click()
    expect(kinerja).to_be_checked()
    page.once("dialog", lambda prompt: prompt.accept())
    dialog.get_by_role("button", name="Batal", exact=True).click()
    expect(dialog).to_have_count(0)
    assert db_call(lambda: AuditEvent.objects.count()) == 0
    edit.click()
    expect(kinerja).not_to_be_checked()
    kinerja.check()
    second = dialog.get_by_role("group", name="Pengaturan divisi Synthetic Second", exact=True)
    second.get_by_role("switch", name="Pelimpahan", exact=True).check()
    captures = Path(".local/divisi-settings-acceptance")
    captures.mkdir(parents=True, exist_ok=True)
    measurements = []
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 850})
        assert dialog.bounding_box()["width"] <= width
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        measurement = first.locator(".division-settings").evaluate(
            """element => ({
                labels: [...element.querySelectorAll('label')].map(label => ({
                    height: label.getBoundingClientRect().height,
                    width: label.getBoundingClientRect().width,
                    color: getComputedStyle(label).color
                })),
                controls: [...element.querySelectorAll('input')].map(input => ({
                    checked: input.checked,
                    background: getComputedStyle(input).backgroundColor,
                    border: getComputedStyle(input).borderColor,
                    thumb: getComputedStyle(input, '::before').backgroundColor
                }))
            })"""
        )
        assert all(
            label["height"] >= 44 and label["width"] >= 44 for label in measurement["labels"]
        )
        measurements.append({"width": width, **measurement})
        page.screenshot(path=str(captures / f"settings-{width}.png"), full_page=True)
    page.emulate_media(forced_colors="active")
    assert kinerja.evaluate("element => getComputedStyle(element).appearance") == "auto"
    page.emulate_media(forced_colors="none")
    page.evaluate("document.documentElement.style.fontSize = '200%'")
    page.set_viewport_size({"width": 390, "height": 850})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    kinerja.scroll_into_view_if_needed()
    expect(kinerja).to_be_visible()
    page.evaluate("document.documentElement.style.fontSize = ''")
    page.set_viewport_size({"width": 1440, "height": 1000})
    (captures / "measurements.json").write_text(
        json.dumps(measurements, indent=2), encoding="utf-8"
    )
    assert db_call(lambda: AuditEvent.objects.count()) == 0
    dialog.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(dialog).to_have_count(0)
    page.reload()
    edit.click()
    expect(kinerja).to_be_checked()
    expect(pelimpahan).not_to_be_checked()
    expect(second.get_by_role("switch", name="Kinerja", exact=True)).not_to_be_checked()
    expect(second.get_by_role("switch", name="Pelimpahan", exact=True)).to_be_checked()
    assert db_call(lambda: AuditEvent.objects.count()) == 2
    audit = db_call(
        lambda: (
            AuditEvent.objects.filter(target_id=first_id)
            .values("actor_id", "action", "changes")
            .get()
        )
    )
    assert audit == {
        "actor_id": synthetic_data.users["hr"].user.pk,
        "action": "division.settings_changed",
        "changes": {"kinerja_enabled": {"old": False, "new": True}},
    }
    kinerja.uncheck()
    pelimpahan.check()
    dialog.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(dialog).to_have_count(0)
    page.reload()
    edit.click()
    expect(kinerja).not_to_be_checked()
    expect(pelimpahan).to_be_checked()
    dialog.press("Escape")
    expect(dialog).to_have_count(0)
    expect(edit).to_be_focused()
    payload = {
        "name": "Synthetic Settings Branch",
        "divisions": [
            {"id": first_id, "name": "Synthetic First", "kinerja_enabled": True},
            {"id": second_id, "name": "Synthetic Second"},
        ],
        "deleted": [],
        "expected": {
            "name": "Synthetic Settings Branch",
            "divisions": {first_id: "Synthetic First", second_id: "Synthetic Second"},
            "settings": {
                first_id: {"kinerja_enabled": False, "pelimpahan_enabled": True},
                second_id: {"kinerja_enabled": False, "pelimpahan_enabled": True},
            },
        },
    }
    before = db_call(lambda: AuditEvent.objects.count())
    logout(page)
    login(page, role="manager")
    expect(page.get_by_role("link", name="Cabang & Divisi", exact=True)).to_have_count(0)
    csrf = page.request.get(live_server.url + "/api/auth/csrf/").json()["csrfToken"]
    rejected = page.request.patch(
        live_server.url + f"/api/organization/branches/{branch_id}/structure/",
        data=payload,
        headers={"X-CSRFToken": csrf},
    )
    assert rejected.status == 403
    assert db_call(lambda: AuditEvent.objects.count()) == before
    assert db_call(lambda: Division.objects.get(pk=first_id).kinerja_enabled) is False
    assert (
        db_call(lambda: Employee.objects.get(pk=synthetic_data.records["own"].pk).division_id)
        is not None
    )
    assert not errors, errors


def test_divisi_settings_lost_response_recovers_without_replaying_write(
    page, login, db_call, synthetic_data
):
    branch_id, first_id, _ = db_call(lambda: prepare_divisions(synthetic_data))
    login(page)
    page.get_by_role("link", name="Cabang & Divisi", exact=True).click()
    edit = page.get_by_role("button", name="Edit cabang Synthetic Settings Branch", exact=True)
    edit.click()
    dialog = page.get_by_role("dialog", name="Edit cabang", exact=True)
    first = dialog.get_by_role("group", name="Pengaturan divisi Synthetic First", exact=True)
    first.get_by_role("switch", name="Kinerja", exact=True).check()
    writes = []

    def lose_response(route):
        writes.append(route.request.method)
        assert route.fetch().status == 200
        route.abort("failed")

    page.route(f"**/api/organization/branches/{branch_id}/structure/", lose_response)
    dialog.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(dialog.get_by_role("button", name="Periksa data tersimpan", exact=True)).to_be_visible()
    expect(dialog.get_by_role("button", name="Simpan perubahan", exact=True)).to_be_disabled()
    expect(first.get_by_role("switch", name="Kinerja", exact=True)).to_be_disabled()
    assert db_call(lambda: Division.objects.get(pk=first_id).kinerja_enabled) is True
    assert (
        db_call(lambda: AuditEvent.objects.filter(action="division.settings_changed").count()) == 1
    )
    dialog.get_by_role("button", name="Periksa data tersimpan", exact=True).click()
    expect(dialog).to_have_count(0)
    assert writes == ["PATCH"]
    page.reload()
    edit.click()
    expect(first.get_by_role("switch", name="Kinerja", exact=True)).to_be_checked()
    assert (
        db_call(lambda: AuditEvent.objects.filter(action="division.settings_changed").count()) == 1
    )
