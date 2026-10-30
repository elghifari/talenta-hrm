from pathlib import Path
from uuid import uuid4

import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from organization.models import Branch, Division
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def test_activity_log_real_settings_write_filters_and_responsive_layout(
    page, login, db_call, live_server, synthetic_data
):
    def prepare():
        branch = Branch.objects.create(name="Synthetic Audit Branch")
        division = Division.objects.create(name="Synthetic Audit Division", branch=branch)
        return str(division.pk)

    division_id = db_call(prepare)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page, role="hr_manager")
    page.get_by_role("link", name="Cabang & Divisi", exact=True).click()
    page.get_by_role("button", name="Edit cabang Synthetic Audit Branch", exact=True).click()
    page.get_by_role("switch", name="Kinerja", exact=True).press("Space")
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    page.get_by_role("link", name="Log aktivitas", exact=True).click()
    expect(page.get_by_role("heading", name="Log aktivitas", exact=True)).to_be_focused()
    expect(page.get_by_text("Kinerja: Nonaktif → Aktif", exact=True)).to_be_visible()
    expect(page.get_by_role("navigation", name="Breadcrumb")).to_have_text("PersonnelLog aktivitas")
    api = page.request.get(live_server.url + "/api/audit-events/")
    assert api.status == 200 and api.headers["cache-control"] == "no-store"
    event = api.json()["results"][0]
    assert event["action"] == "division.settings_changed"
    assert event["actor"]["id"] == synthetic_data.users["hr_manager"].user.pk
    assert event["target"]["id"] == division_id
    assert db_call(lambda: AuditEvent.objects.count()) == 1
    recorded = db_call(lambda: AuditEvent.objects.values("actor_id", "created_at").get())
    assert event["created_at"] == recorded["created_at"].isoformat()
    page.reload()
    expect(page.get_by_text("Synthetic Audit Division", exact=True)).to_be_visible()
    expect(page.locator(".audit-table time")).to_contain_text("WIB")
    captures = Path(".local/activity-log-acceptance")
    captures.mkdir(parents=True, exist_ok=True)
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        for button in page.locator(".activity-log button").all():
            assert button.bounding_box()["height"] >= 44
        page.screenshot(path=str(captures / f"activity-{width}.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 900})
    page.evaluate("document.documentElement.style.fontSize = '200%'")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.evaluate("document.documentElement.style.fontSize = ''")
    page.get_by_label("Pelaku (email)", exact=True).fill("absent@example.test")
    page.get_by_role("button", name="Terapkan filter", exact=True).click()
    expect(
        page.get_by_text("Tidak ada aktivitas yang cocok dengan filter.", exact=True)
    ).to_be_visible()
    page.get_by_role("button", name="Reset", exact=True).click()
    expect(page.get_by_text("Synthetic Audit Division", exact=True)).to_be_visible()
    page.get_by_label("Aktivitas", exact=True).select_option("division.settings_changed")
    page.get_by_label("Dari tanggal", exact=True).fill("2026-10-28")
    page.get_by_label("Sampai tanggal", exact=True).fill("2026-10-27")
    page.get_by_role("button", name="Terapkan filter", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("Filter tidak valid.")
    page.get_by_role("button", name="Reset", exact=True).click()
    expect(page.get_by_text("Synthetic Audit Division", exact=True)).to_be_visible()
    assert db_call(lambda: AuditEvent.objects.count()) == 1
    assert not errors, errors


def test_activity_log_pagination_history_and_unavailable_page_recovery(
    page, login, db_call, synthetic_data
):
    user = synthetic_data.users["hr_manager"].user
    db_call(
        lambda: AuditEvent.objects.bulk_create(
            [
                AuditEvent(actor=user, action="division.deleted", target_id=uuid4())
                for _ in range(51)
            ]
        )
    )
    login(page, role="hr_manager")
    page.get_by_role("link", name="Log aktivitas", exact=True).click()
    expect(page.locator(".audit-table tbody tr")).to_have_count(50)
    expect(page.get_by_text("Rincian perubahan tidak tercatat.", exact=True)).to_have_count(50)
    expect(page.locator(".audit-table a")).to_have_count(0)
    page.get_by_role("button", name="Berikutnya", exact=True).click()
    expect(page.locator(".audit-table tbody tr")).to_have_count(1)
    page.get_by_role("button", name="Sebelumnya", exact=True).click()
    expect(page.locator(".audit-table tbody tr")).to_have_count(50)
    db_call(lambda: AuditEvent.objects.all().delete())
    page.get_by_role("button", name="Berikutnya", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("Halaman log ini tidak tersedia.")
    page.get_by_role("button", name="Halaman pertama", exact=True).click()
    expect(page.get_by_text("Belum ada aktivitas tercatat.", exact=True)).to_be_visible()
    page.route("**/api/audit-events/?*", lambda route: route.fulfill(status=503, json={}))
    page.get_by_role("button", name="Reset", exact=True).click()
    expect(page.get_by_role("button", name="Coba lagi", exact=True)).to_be_visible()
    page.unroute("**/api/audit-events/?*")
    page.get_by_role("button", name="Coba lagi", exact=True).click()
    expect(page.get_by_text("Belum ada aktivitas tercatat.", exact=True)).to_be_visible()


def test_activity_log_revocation_discards_delayed_response(
    page, login, db_call, live_server, synthetic_data
):
    user = synthetic_data.users["hr_manager"].user
    db_call(
        lambda: AuditEvent.objects.create(actor=user, action="division.deleted", target_id=uuid4())
    )
    login(page, role="hr_manager")
    page.get_by_role("link", name="Log aktivitas", exact=True).click()
    expect(page.locator(".audit-table tbody tr")).to_have_count(1)
    held = []
    saved_body = page.request.get(live_server.url + "/api/audit-events/").body()

    def delay(route):
        held.append(route)
        page.evaluate("window.auditResponseHeld = true")

    page.route("**/api/audit-events/?*", delay)
    page.get_by_role("button", name="Terapkan filter", exact=True).click()
    expect(page.get_by_text("Memuat log aktivitas…", exact=True)).to_be_visible()
    page.wait_for_function("window.auditResponseHeld === true")
    assert held
    db_call(lambda: user.groups.remove(Group.objects.get(name="HR_MANAGER")))
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page.get_by_role("alert")).to_have_text("Akses log aktivitas tidak tersedia.")
    expect(page.get_by_role("link", name="Log aktivitas", exact=True)).to_have_count(0)
    for route in held:
        route.fulfill(status=200, body=saved_body, content_type="application/json")
    expect(page.locator(".audit-table")).to_have_count(0)
    response = page.request.get(live_server.url + "/api/audit-events/")
    assert response.status == 403
    assert "results" not in response.json() and "count" not in response.json()


def test_activity_log_denial_logout_and_expiry(
    page, login, logout, db_call, live_server, synthetic_data
):
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    login(page)
    page.goto(live_server.url + "/personnel/activity")
    expect(page.get_by_role("alert")).to_have_text("Akses log aktivitas tidak tersedia.")
    assert not any("/api/audit-events/" in url for url in requests)
    assert page.request.get(live_server.url + "/api/audit-events/").status == 403
    logout(page)
    login(page, role="hr_manager")
    page.get_by_role("link", name="Log aktivitas", exact=True).click()
    expect(page.get_by_text("Belum ada aktivitas tercatat.", exact=True)).to_be_visible()
    logout(page)
    assert page.request.get(live_server.url + "/api/audit-events/").status == 403
    login(page, role="hr_manager")
    page.get_by_role("link", name="Log aktivitas", exact=True).click()
    expect(page.get_by_text("Belum ada aktivitas tercatat.", exact=True)).to_be_visible()
    db_call(lambda: Session.objects.all().delete())
    page.get_by_role("button", name="Reset", exact=True).click()
    expect(page.get_by_role("button", name="Masuk", exact=True)).to_be_visible()
    expect(page.locator(".audit-table")).to_have_count(0)
