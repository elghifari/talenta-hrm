from datetime import timedelta
from types import SimpleNamespace

import dj_database_url
import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.db import connection
from django.utils import timezone
from employees.models import Employee, EmployeeAssignment
from organization.models import Unit, UnitAccess
from playwright.sync_api import expect


@pytest.fixture
def synthetic_data(django_user_model):
    today = timezone.localdate()
    users = {}
    for role, group in [
        ("hr", "HR"),
        ("manager", "KEPALA_UNIT"),
        ("finance", "FINANCE"),
        ("hr_manager", "HR"),
    ]:
        email = f"{role}@example.test"
        user = django_user_model.objects.create_user(
            email=email, password="Synthetic-browser-only-42"
        )
        user.groups.add(Group.objects.get_or_create(name=group)[0])
        if role == "hr_manager":
            user.groups.add(Group.objects.get_or_create(name="HR_MANAGER")[0])
        users[role] = SimpleNamespace(user=user, email=email, password="Synthetic-browser-only-42")
    a = Unit.objects.create(code="SYN-A", name="Synthetic A")
    b = Unit.objects.create(code="SYN-B", name="Synthetic B", parent=a)
    c = Unit.objects.create(code="SYN-C", name="Synthetic C")
    UnitAccess.objects.create(user=users["manager"].user, unit=a)
    UnitAccess.objects.create(user=users["manager"].user, unit=c)
    records = {}
    for code, key, unit, start, end in [
        ("0001", "own", a, today - timedelta(days=365), None),
        ("0002", "outside", b, today - timedelta(days=365), None),
        ("0003", "second", c, today - timedelta(days=365), None),
        ("0004", "old", a, today - timedelta(days=365), today - timedelta(days=1)),
        ("0005", "future", a, today + timedelta(days=1), None),
        ("0006", "unassigned", None, today, None),
    ]:
        employee = Employee.objects.create(
            employee_code=code, full_name=f"Pegawai Contoh {key.title()}"
        )
        records[key] = employee
        if unit:
            EmployeeAssignment.objects.create(
                employee=employee, unit=unit, effective_from=start, effective_until=end
            )
    return SimpleNamespace(users=users, records=records)


@pytest.fixture
def login(live_server, synthetic_data):
    def perform(page, role="hr", url=None):
        account = synthetic_data.users[role]
        page.goto((url or live_server.url) + "/employees")
        page.get_by_label("Email", exact=True).fill(account.email)
        page.get_by_label("Sandi", exact=True).fill(account.password)
        page.get_by_role("button", name="Masuk", exact=True).click()
        expect(page.get_by_text(account.email, exact=True)).to_be_visible()
        return account

    return perform


@pytest.fixture
def logout():
    def perform(page):
        page.get_by_role("button", name="Keluar", exact=True).click()
        expect(page.get_by_label("Email", exact=True)).to_be_visible()

    return perform


@pytest.fixture(autouse=True)
def isolated_browser_database(django_db_setup, django_db_blocker):
    import os

    configured = dj_database_url.parse(
        os.environ.get("DATABASE_URL", "postgresql://hrm_dev@127.0.0.1:55439/hrm_dev")
    )["NAME"]
    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            actual = cursor.fetchone()[0]
        assert actual != configured and actual.startswith("test_"), (
            "Browser tests require pytest's disposable test database"
        )
    assert settings.FRONTEND_DEV_ENABLED


@pytest.fixture
def page(live_server, synthetic_data, isolated_browser_database):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(10000)
        yield page
        context.close()
        browser.close()


@pytest.fixture
def db_call():
    from concurrent.futures import ThreadPoolExecutor

    from django.db import connections

    def perform(function, *args, **kwargs):
        def invoke():
            try:
                return function(*args, **kwargs)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(invoke).result()

    return perform
