import json
from pathlib import Path

import pytest
from employees.models import Employee
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


def verify_sidebar_contrast(page, captures, label):
    pairs = page.evaluate("""() => {
      const rgb = value => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
      const luminance = color => rgb(color).map(channel => {
        const value = channel / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
      const selectors = [
        '.sidebar .brand', '.sidebar .brand span', '.sidebar button',
        '.sidebar a', '.sidebar-flyout p', '.sidebar-flyout a'
      ].join(', ');
      return [...document.querySelectorAll(selectors)]
        .filter(element => element.getBoundingClientRect().height > 0).map(element => {
          let parent = element;
          while (parent && ['rgba(0, 0, 0, 0)', 'transparent'].includes(
            getComputedStyle(parent).backgroundColor
          )) parent = parent.parentElement;
          const foreground = getComputedStyle(element).color;
          const background = parent
            ? getComputedStyle(parent).backgroundColor : 'rgb(255, 255, 255)';
          const first = luminance(foreground), second = luminance(background);
          return {label: element.getAttribute('aria-label') || element.textContent.trim(),
            foreground, background,
            ratio: (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05)};
        });
    }""")
    assert pairs and all(pair["ratio"] >= 4.5 for pair in pairs), pairs
    (captures / f"contrast-{label}.json").write_text(json.dumps(pairs, indent=2), encoding="utf-8")


def test_sidebar_stays_in_view_while_the_employee_page_scrolls(page, login, db_call):
    db_call(
        lambda: Employee.objects.bulk_create(
            [
                Employee(
                    employee_code=f"SYN-SIDEBAR-{index:03d}",
                    full_name=f"Synthetic sidebar employee {index}",
                )
                for index in range(40)
            ]
        )
    )
    login(page, role="hr_manager")
    sidebar = page.locator(".sidebar")
    before = sidebar.bounding_box()
    page.evaluate("window.scrollTo(0, 600)")
    page.wait_for_function("window.scrollY > 300")
    after = sidebar.bounding_box()
    assert abs(after["y"] - before["y"]) <= 1
    assert after["height"] <= page.evaluate("innerHeight")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.set_viewport_size({"width": 768, "height": 280})
    page.locator(".sidebar").evaluate("element => element.scrollTop = element.scrollHeight")
    assert sidebar.evaluate("element => element.scrollTop > 0")
    expect(sidebar.get_by_role("link", name="Log aktivitas", exact=True)).to_be_in_viewport()


def test_sidebar_dropdown_rail_and_mobile_keyboard_navigation(page, login):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    login(page, role="hr_manager")
    nav = page.get_by_role("navigation", name="Modul", exact=True)
    group = nav.get_by_role("button", name="Personnel", exact=True)
    expect(page.get_by_text("Ruang kerja", exact=True)).to_have_count(0)
    expect(group).to_have_attribute("aria-expanded", "true")
    group.click()
    expect(nav.get_by_role("link", name="Ringkasan", exact=True)).to_have_count(0)
    group.press("Space")
    nav.get_by_role("link", name="Ringkasan", exact=True).click()
    expect(page.get_by_role("heading", name="Personnel", exact=True)).to_be_visible()
    nav.get_by_role("link", name="Data pegawai", exact=True).click()
    expect(page.get_by_role("link", name="Pegawai Contoh Own", exact=True)).to_be_visible()
    captures = Path(".local/sidebar-acceptance")
    captures.mkdir(parents=True, exist_ok=True)
    for width in (1440, 768):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        verify_sidebar_contrast(page, captures, f"expanded-{width}")
        page.screenshot(path=str(captures / f"expanded-{width}.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 900})
    page.get_by_role("button", name="Ciutkan sidebar", exact=True).click()
    assert page.locator(".sidebar").bounding_box()["width"] == 72
    group.focus()
    group.press("Enter")
    flyout = page.get_by_role("navigation", name="Personnel", exact=True)
    expect(flyout.get_by_role("link", name="Ringkasan", exact=True)).to_be_focused()
    for width in (1440, 768):
        page.set_viewport_size({"width": width, "height": 900})
        bounds = flyout.bounding_box()
        assert bounds["x"] >= page.locator(".sidebar").bounding_box()["width"]
        assert bounds["x"] + bounds["width"] <= width
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        verify_sidebar_contrast(page, captures, f"compact-{width}")
        page.screenshot(path=str(captures / f"compact-{width}.png"), full_page=True)
    page.keyboard.press("Escape")
    expect(flyout).to_have_count(0)
    expect(group).to_be_focused()
    group.press("Enter")
    page.get_by_role("main").click(position={"x": 350, "y": 60})
    expect(flyout).to_have_count(0)
    group.click()
    flyout.get_by_role("link", name="Log aktivitas", exact=True).click()
    expect(page.get_by_role("heading", name="Log aktivitas", exact=True)).to_be_visible()
    expect(flyout).to_have_count(0)
    page.get_by_role("button", name="Perluas sidebar", exact=True).click()
    for width in (390, 320):
        page.set_viewport_size({"width": width, "height": 844})
        page.get_by_role("button", name="Menu", exact=True).click()
        expect(group).to_be_visible()
        expect(page.get_by_role("button", name="Ciutkan sidebar", exact=True)).to_have_count(0)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        verify_sidebar_contrast(page, captures, f"mobile-{width}")
        page.screenshot(path=str(captures / f"mobile-{width}.png"), full_page=True)
        page.keyboard.press("Escape")
        expect(page.get_by_role("button", name="Menu", exact=True)).to_be_focused()
    page.get_by_role("button", name="Menu", exact=True).click()
    nav.get_by_role("link", name="Data pegawai", exact=True).click()
    expect(page.get_by_role("button", name="Menu", exact=True)).to_have_attribute(
        "aria-expanded", "false"
    )
    expect(page.get_by_role("heading", name="Data pegawai", exact=True)).to_be_visible()
    page.evaluate("document.documentElement.style.fontSize = '200%'")
    page.get_by_role("button", name="Menu", exact=True).click()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    for control in nav.locator("button, a").all():
        if control.is_visible():
            assert control.bounding_box()["height"] >= 44
    assert not errors, errors


def test_compact_sidebar_navigation_keeps_unsaved_employee_guard(page, login, db_call):
    login(page)
    page.get_by_role("link", name="Tambah pegawai", exact=True).click()
    page.get_by_label("Nama lengkap", exact=True).fill("Synthetic unsaved sidebar draft")
    page.get_by_role("button", name="Ciutkan sidebar", exact=True).click()
    page.get_by_role("navigation", name="Modul", exact=True).get_by_role(
        "button", name="Personnel", exact=True
    ).click()
    page.get_by_role("navigation", name="Personnel", exact=True).get_by_role(
        "link", name="Ringkasan", exact=True
    ).click()
    expect(page.get_by_role("alertdialog")).to_be_visible()
    page.get_by_role("button", name="Tetap mengedit", exact=True).click()
    expect(page.get_by_label("Nama lengkap", exact=True)).to_have_value(
        "Synthetic unsaved sidebar draft"
    )
    assert db_call(lambda: Employee.objects.count()) == 6
