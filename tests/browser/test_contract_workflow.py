import json
from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from contracts.constants import TOKENS
from contracts.fields import AMOUNTS, field_spec
from contracts.models import ContractDocument, ContractDraft
from docx import Document
from employees.models import Employee
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(params=["yayasan", "guru", "klinik_umum"])
def contract_browser_data(request, settings, tmp_path, live_server, db_call):
    kind = request.param
    root = tmp_path / "references"
    directory = root / "synthetic-v1"
    directory.mkdir(parents=True)
    templates = {}
    for template_kind in TOKENS:
        document = Document()
        paragraph = document.add_paragraph()
        paragraph.add_run("{{na")
        paragraph.add_run("ma}}")
        for token in sorted(TOKENS[template_kind] - {"nama", "uraian_tugas"}):
            document.add_paragraph("{{" + token + "}}")
        document.add_table(rows=1, cols=1).cell(0, 0).text = "{{uraian_tugas}}"
        document.sections[0].header.paragraphs[0].text = "Synthetic " + template_kind
        document.sections[0].footer.paragraphs[0].text = "Synthetic footer"
        stream = BytesIO()
        document.save(stream)
        name = template_kind + ".docx"
        (directory / name).write_bytes(stream.getvalue())
        templates[template_kind] = {"file": name, "sha256": sha256(stream.getvalue()).hexdigest()}
    manifest = {"version": "synthetic-v1", "templates": templates}
    for name in ("units", "jobs"):
        content = b"[]"
        (directory / (name + ".json")).write_bytes(content)
        manifest[name + "_file"] = name + ".json"
        manifest[name + "_sha256"] = sha256(content).hexdigest()
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "active.json").write_text(json.dumps({"version": "synthetic-v1"}), encoding="utf-8")
    settings.CONTRACT_REFERENCE_ROOT = root

    def create():
        from compensation.models import CompensationAssignment

        employee = Employee.objects.create(
            employee_code="PKWT-SYN-00042",
            full_name="Synthetic A & B {{nama}}",
            employment_status="kontrak",
            pkwt_type=kind,
            contract_expiry=date.today(),
        )
        return (
            str(employee.id),
            Employee.objects.values().get(pk=employee.id),
            list(CompensationAssignment.objects.values()),
        )

    employee_id, before, compensation = db_call(create)
    values = {f["key"]: "Synthetic text" for f in field_spec(kind)}
    values.update({key: "0" for key in AMOUNTS})
    values.update(
        {
            "nama": before["full_name"],
            "nip": "0000123",
            "tgl_surat": "2026-11-05",
            "tgl_lahir": "1995-01-01",
            "tgl_mulai": "2026-12-01",
            "tgl_berakhir": "2027-11-30",
            "jenis_kelamin": "Perempuan",
            "hari_kerja_jml": "6",
            "hari_kerja_rentang": "Senin - Sabtu",
            "jam_sen_jum": "08.00-17.00",
            "jam_sabtu_jam": "",
            "jam_ist": "12.00-13.00",
            "jam_ist_jumat": "11.30-13.00",
            "tambahan_mode": "pasal3",
            "tambahan_text": "",
            "jobdesk": "Synthetic long duties <text> & literal {{nama}} 😀\n" * 120,
        }
    )

    def fill_required_fields(page):
        for field in field_spec(kind):
            control = page.locator("#contract-" + field["key"])
            if field["kind"] == "choice":
                control.select_option(values[field["key"]])
            else:
                control.fill(values[field["key"]])

    def unchanged():
        from compensation.models import CompensationAssignment

        assert Employee.objects.values().get(pk=employee_id) == before
        assert list(CompensationAssignment.objects.values()) == compensation

    return SimpleNamespace(
        employee_id=employee_id,
        kind=kind,
        employee_url=f"{live_server.url}/employees/{employee_id}",
        editor_url=f"{live_server.url}/employees/{employee_id}/contracts/new",
        expected_name=before["full_name"],
        reference_directory=directory,
        fill_required_fields=fill_required_fields,
        assert_no_employee_or_payroll_change=unchanged,
        values=values,
    )


def test_hr_generates_and_downloads_saved_contract(page, login, db_call, contract_browser_data):
    data = contract_browser_data
    login(page, "hr")
    page.goto(data.employee_url)
    page.get_by_role("link", name="Buat draf perpanjangan", exact=True).click()
    data.fill_required_fields(page)
    documents = page.get_by_role("region", name="Dokumen tersimpan", exact=True)
    expect(documents).to_have_count(0)
    page.get_by_role("button", name="Simpan draf", exact=True).click()
    expect(page.get_by_text("Draf tersimpan.", exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_label("NIP", exact=True)).to_have_value("0000123")
    expect(documents).to_have_count(0)
    page.get_by_role("button", name="Buat DOCX", exact=True).click()
    expect(page.get_by_text("DOCX dibuat.", exact=True)).to_be_visible()
    expect(documents).to_be_visible()
    assert documents.evaluate(
        "node => Boolean(node.compareDocumentPosition("
        "document.querySelector('.contract-actionbar')) & Node.DOCUMENT_POSITION_FOLLOWING)"
    )
    expect(documents.get_by_role("button", name="Download DOCX", exact=True)).to_have_attribute(
        "type", "button"
    )
    download_writes = []
    page.on(
        "request",
        lambda request: (
            download_writes.append(request.url)
            if request.method in {"POST", "PATCH"} and "/api/contract-drafts/" in request.url
            else None
        ),
    )
    with page.expect_download() as event:
        page.get_by_role("button", name="Download DOCX", exact=True).first.click()
    content = Path(event.value.path()).read_bytes()
    assert download_writes == []
    output = Document(BytesIO(content))
    assert data.expected_name in "\n".join(p.text for p in output.paragraphs)
    assert output.tables[0].cell(0, 0).text == data.values["jobdesk"]
    assert output.sections[0].header.paragraphs[0].text == "Synthetic " + data.kind
    first = db_call(lambda: ContractDocument.objects.get().content_sha256)
    assert sha256(content).hexdigest() == first
    db_call(data.assert_no_employee_or_payroll_change)
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert documents.evaluate("node => node.scrollWidth <= node.clientWidth")
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        assert documents.evaluate(
            "node => node.getBoundingClientRect().bottom <= "
            "document.querySelector('.contract-actionbar').getBoundingClientRect().top"
        )
        captures = Path(".local/contract-documents-layout")
        captures.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(captures / f"{data.kind}-{width}.png"))
    page.get_by_label("NIP", exact=True).fill("0000999")
    page.get_by_role("button", name="Simpan draf", exact=True).click()
    expect(page.get_by_text("Draf tersimpan.", exact=True)).to_be_visible()
    page.get_by_role("button", name="Buat DOCX", exact=True).click()
    expect(page.get_by_role("button", name="Download DOCX", exact=True)).to_have_count(2)
    assert (
        db_call(lambda: ContractDocument.objects.order_by("generated_at").first().content_sha256)
        == first
    )
    page.goto(data.employee_url)
    page.get_by_role("button", name="Riwayat dokumen", exact=True).click()
    expect(page.locator(".contract-history li a")).to_have_count(3)
    page.goto(data.employee_url.split("/employees/")[0] + "/personnel")
    row = page.get_by_role("row").filter(has_text=data.expected_name)
    expect(row.get_by_role("link", name="Buat draf perpanjangan", exact=True)).to_be_visible()
    row.get_by_role("link", name="Buat draf perpanjangan", exact=True).click()
    expect(page.get_by_label("NIP", exact=True)).to_have_value("")


def test_lost_create_and_generation_responses_recover_by_get(
    page, login, db_call, contract_browser_data
):
    data = contract_browser_data
    login(page, "hr")
    page.goto(data.editor_url)
    data.fill_required_fields(page)
    counts = {"create": 0, "generate": 0}

    def lose_create(route):
        if route.request.method != "POST":
            route.continue_()
            return
        counts["create"] += 1
        assert route.fetch().status == 201
        route.abort("failed")

    page.route("**/api/contract-drafts/", lose_create)
    page.get_by_role("button", name="Simpan draf", exact=True).click()
    page.get_by_role("button", name="Periksa hasil", exact=True).click()
    expect(page.get_by_text("Draf tersimpan.", exact=True)).to_be_visible()
    assert counts["create"] == 1

    def lose_generate(route):
        counts["generate"] += 1
        assert route.fetch().status == 200
        route.abort("failed")

    page.route("**/generate/", lose_generate)
    page.get_by_role("button", name="Buat DOCX", exact=True).click()
    page.get_by_role("button", name="Periksa hasil", exact=True).click()
    expect(page.get_by_text("DOCX dibuat.", exact=True)).to_be_visible()
    assert counts == {"create": 1, "generate": 1}
    assert db_call(ContractDraft.objects.count) == db_call(ContractDocument.objects.count) == 1
    db_call(data.assert_no_employee_or_payroll_change)


def test_late_generation_after_logout_does_not_restore_data(
    page, login, logout, contract_browser_data
):
    data = contract_browser_data
    login(page, "hr")
    page.goto(data.editor_url)
    data.fill_required_fields(page)
    page.get_by_role("button", name="Simpan draf", exact=True).click()
    expect(page.get_by_text("Draf tersimpan.", exact=True)).to_be_visible()
    held, downloads = [], []
    page.on("download", lambda download: downloads.append(download))

    def hold(route):
        response = route.fetch()
        assert response.status == 200
        held.append((route, response))
        page.evaluate("window.__contractGenerationCommitted = true")

    page.route("**/generate/", hold)
    page.get_by_role("button", name="Buat DOCX", exact=True).click()
    page.wait_for_function("window.__contractGenerationCommitted === true")
    logout(page)
    assert len(held) == 1
    held[0][0].fulfill(response=held[0][1])
    expect(page.get_by_label("Email", exact=True)).to_be_visible()
    expect(page.get_by_label("NIP", exact=True)).to_have_count(0)
    assert downloads == []


def test_permission_loss_while_blob_pending_prevents_download(
    page, login, db_call, synthetic_data, contract_browser_data
):
    data = contract_browser_data
    login(page, "hr")
    page.goto(data.editor_url)
    data.fill_required_fields(page)
    page.get_by_role("button", name="Simpan draf", exact=True).click()
    expect(page.get_by_text("Draf tersimpan.", exact=True)).to_be_visible()
    page.get_by_role("button", name="Buat DOCX", exact=True).click()
    expect(page.get_by_text("DOCX dibuat.", exact=True)).to_be_visible()
    downloads = []
    page.on("download", lambda download: downloads.append(download))
    page.evaluate("""() => {
        const original = Response.prototype.blob;
        Response.prototype.blob = async function () {
            const actual = await original.call(this);
            return new Promise(resolve => {
                window.__releaseContractBlob = () => resolve(actual);
            });
        };
    }""")
    page.get_by_role("button", name="Download DOCX", exact=True).click()
    page.wait_for_function("typeof window.__releaseContractBlob === 'function'")
    db_call(synthetic_data.users["hr"].user.groups.clear)
    page.evaluate("window.__releaseContractBlob()")
    expect(page.get_by_role("heading", name="Akses tidak tersedia", exact=True)).to_be_visible()
    expect(page.get_by_label("NIP", exact=True)).to_have_count(0)
    assert downloads == []


def test_editor_responsive_contrast_and_keyboard(page, login, contract_browser_data):
    data = contract_browser_data
    login(page, "hr")
    page.goto(data.editor_url)
    expect(page.get_by_label("NIP", exact=True)).to_be_visible()
    page.keyboard.press("Tab")
    page.get_by_label("Uraian Tugas", exact=True).focus()
    outline = page.get_by_label("Uraian Tugas", exact=True).evaluate(
        "e => ({width: parseFloat(getComputedStyle(e).outlineWidth), "
        "style: getComputedStyle(e).outlineStyle})"
    )
    assert outline["width"] >= 3 and outline["style"] != "none"
    evidence = Path(__file__).resolve().parents[2] / ".local/pkwt-acceptance"
    evidence.mkdir(parents=True, exist_ok=True)
    for width in (390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        mobile_sections = page.get_by_role("combobox", name="Bagian form", exact=True)
        section_menu = page.get_by_role("navigation", name="Bagian form kontrak", exact=True)
        if width >= 1180:
            expect(mobile_sections).not_to_be_visible()
            expect(section_menu).to_be_visible()
        else:
            expect(mobile_sections).to_be_visible()
            expect(section_menu).not_to_be_visible()
        controls = page.locator(
            ".contract-editor input:visible, .contract-editor select:visible, "
            ".contract-editor textarea:visible"
        ).evaluate_all(
            "nodes => nodes.map(e => ({id: e.id, height: e.getBoundingClientRect().height}))"
        )
        assert controls and all(control["height"] >= 44 for control in controls), controls
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=str(evidence / f"{data.kind}-{width}.png"))
    pairs = page.locator(".contract-editor").evaluate("""root => {
        const channel = x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4;
        const rgb = x => x.match(/[0-9.]+/g).map(Number);
        const luminance = c => .2126 * channel(c[0] / 255)
            + .7152 * channel(c[1] / 255) + .0722 * channel(c[2] / 255);
        const nodes = root.querySelectorAll(
            'label, legend, h1, h2, p, button, a, input, select, textarea');
        return Array.from(nodes).filter(e => e.getClientRects().length && !e.disabled).map(e => {
            const style = getComputedStyle(e), foreground = rgb(style.color);
            let node = e, background;
            while (node) {
                const color = rgb(getComputedStyle(node).backgroundColor);
                if (color.length === 3 || color[3] > .99) { background = color; break; }
                node = node.parentElement;
            }
            background ??= [255, 255, 255];
            const a = luminance(foreground), b = luminance(background);
            const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
            const large = parseFloat(style.fontSize) >= 24 ||
                (parseFloat(style.fontSize) >= 18.66 && Number(style.fontWeight) >= 700);
            return { tag: e.tagName, foreground, background, ratio, minimum: large ? 3 : 4.5 };
        });
    }""")
    (evidence / f"{data.kind}-contrast.json").write_text(json.dumps(pairs, indent=2))
    assert all(pair["ratio"] >= pair["minimum"] for pair in pairs)
    page.get_by_label("NIP", exact=True).focus()
    page.keyboard.type("00042")
    expect(page.get_by_label("NIP", exact=True)).to_have_value("00042")


@pytest.mark.parametrize("contract_browser_data", ["yayasan"], indirect=True)
def test_missing_references_allow_text_save_and_noop_receipt_recovery(
    page, login, db_call, contract_browser_data
):
    data = contract_browser_data
    login(page, "hr")
    page.goto(data.editor_url)
    data.fill_required_fields(page)
    page.get_by_role("button", name="Simpan draf", exact=True).click()
    expect(page.get_by_text("Draf tersimpan.", exact=True)).to_be_visible()
    (data.reference_directory / "guru.docx").unlink()
    page.reload()
    expect(
        page.get_by_text("Referensi kontrak belum tersedia. Riwayat dokumen tetap dapat dibuka.")
    ).to_be_visible()
    page.get_by_label("NIP", exact=True).fill("0000123 ")
    writes = []

    def lose_noop(route):
        if route.request.method != "PATCH":
            route.continue_()
            return
        response = route.fetch()
        assert response.status == 200
        writes.append(response.json())
        route.abort("failed")

    page.route("**/api/contract-drafts/*/", lose_noop)
    page.get_by_role("button", name="Simpan draf", exact=True).click()
    page.get_by_role("button", name="Periksa hasil", exact=True).click()
    expect(page.get_by_text("Draf tersimpan.", exact=True)).to_be_visible()
    assert len(writes) == 1 and writes[0]["revision"] == 1
    page.unroute("**/api/contract-drafts/*/", lose_noop)
    page.get_by_label("NIP", exact=True).fill("0000456")
    page.get_by_role("button", name="Simpan draf", exact=True).click()
    expect(page.get_by_text("Revisi 2", exact=False)).to_be_visible()
    expect(page.get_by_role("button", name="Buat DOCX", exact=True)).to_be_disabled()
    db_call(data.assert_no_employee_or_payroll_change)


@pytest.mark.parametrize("contract_browser_data", ["yayasan"], indirect=True)
def test_saved_override_default_dialog_escape_and_explicit_confirmation(
    page, login, db_call, contract_browser_data
):
    data = contract_browser_data
    units = [
        {"key": key, "unit": key, "alamat_unit": "Default address " + key}
        for key in ("Unit A", "Unit B")
    ]
    path = data.reference_directory / "units.json"
    path.write_text(json.dumps(units))
    manifest_path = data.reference_directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["units_sha256"] = sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    login(page, "hr")
    page.goto(data.editor_url)
    page.get_by_label("Unit", exact=True).select_option("Unit A")
    data.fill_required_fields(page)
    page.get_by_role("button", name="Simpan draf", exact=True).click()
    expect(page.get_by_text("Draf tersimpan.", exact=True)).to_be_visible()
    page.reload()
    page.get_by_label("Unit", exact=True).focus()
    page.get_by_label("Unit", exact=True).select_option("Unit B")
    expect(page.get_by_role("dialog")).to_be_visible()
    expect(page.get_by_label("Alamat Unit", exact=True)).to_have_value("Synthetic text")
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).not_to_be_visible()
    expect(page.get_by_label("Unit", exact=True)).to_have_value("Unit A")
    expect(page.get_by_label("Unit", exact=True)).to_be_focused()
    page.get_by_label("Unit", exact=True).focus()
    page.get_by_label("Unit", exact=True).select_option("Unit B")
    page.get_by_role("button", name="Gunakan default", exact=True).click()
    expect(page.get_by_label("Alamat Unit", exact=True)).to_have_value("Default address Unit B")
    assert db_call(lambda: ContractDraft.objects.get().revision) == 1
    db_call(data.assert_no_employee_or_payroll_change)


def test_dirty_cancel_and_role_denial(page, login, logout, contract_browser_data):
    data = contract_browser_data
    login(page, "hr")
    page.goto(data.editor_url)
    page.get_by_label("NIP", exact=True).fill("0007")
    page.get_by_role("link", name="Batal", exact=True).click()
    page.get_by_role("button", name="Tetap mengedit", exact=True).click()
    expect(page.get_by_label("NIP", exact=True)).to_have_value("0007")
    page.get_by_role("link", name="Batal", exact=True).click()
    page.get_by_role("button", name="Tinggalkan halaman", exact=True).click()
    expect(page.get_by_role("heading", name=data.expected_name, exact=True)).to_be_visible()
    logout(page)
    for role in ("manager", "finance"):
        login(page, role)
        page.goto(data.editor_url)
        expect(page.get_by_role("heading", name="Akses tidak tersedia", exact=True)).to_be_visible()
        assert (
            page.request.get(
                data.employee_url.split("/employees/")[0] + "/api/contract-references/"
            ).status
            == 403
        )
        logout(page)
