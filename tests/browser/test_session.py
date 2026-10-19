import pytest
from django.contrib.sessions.models import Session
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def test_expired_session_clears_draft_and_does_not_replay_write(
    page, live_server, login, synthetic_data, db_call
):
    login(page)
    record = synthetic_data.records["own"]
    page.goto(live_server.url + f"/employees/{record.pk}/edit")
    page.get_by_label("Nama lengkap", exact=True).fill("Synthetic Unsaved Secret")
    db_call(lambda: Session.objects.all().delete())
    page.get_by_role("button", name="Simpan perubahan", exact=True).click()
    expect(page.get_by_role("button", name="Masuk", exact=True)).to_be_visible()
    expect(page.get_by_text("Sesi Anda berakhir. Masuk kembali untuk melanjutkan.")).to_be_visible()
    db_call(record.refresh_from_db)
    assert record.full_name == "Pegawai Contoh Own"
    assert "Synthetic Unsaved Secret" not in page.locator("body").inner_text()
    account = synthetic_data.users["manager"]
    page.get_by_label("Email", exact=True).fill(account.email)
    page.get_by_label("Sandi", exact=True).fill(account.password)
    page.get_by_role("button", name="Masuk", exact=True).click()
    expect(page.get_by_role("heading", name="Akses tidak tersedia", exact=True)).to_be_visible()


def test_invalid_credentials_then_logout_prevents_protected_reads(
    page, live_server, login, synthetic_data, db_call
):
    page.goto(live_server.url + "/login")
    page.get_by_label("Email", exact=True).fill("hr@example.test")
    page.get_by_label("Sandi", exact=True).fill("incorrect-synthetic")
    page.get_by_role("button", name="Masuk", exact=True).click()
    expect(page.get_by_text("Email atau sandi tidak sesuai.")).to_be_visible()
    page.get_by_label("Sandi", exact=True).fill(synthetic_data.users["hr"].password)
    page.get_by_role("button", name="Masuk", exact=True).click()
    expect(page.get_by_role("heading", name="Data pegawai", exact=True)).to_be_visible()
    page.get_by_role("button", name="Keluar", exact=True).click()
    expect(page.get_by_role("button", name="Masuk", exact=True)).to_be_visible()
    assert page.context.request.get(live_server.url + "/api/auth/me/").status == 403
