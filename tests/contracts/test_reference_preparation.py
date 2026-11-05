import importlib.util
from hashlib import sha256
from pathlib import Path

import pytest


def preparation():
    path = Path(__file__).resolve().parents[2] / "scripts/prepare_contract_references.py"
    spec = importlib.util.spec_from_file_location("prepare_contract_references", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_exclusion_requires_matching_fingerprint(tmp_path):
    module = preparation()
    source = tmp_path / "source"
    source.write_bytes(b"original")
    with pytest.raises(ValueError):
        module.verify_source(source, "0" * 64)
    module.verify_source(source, sha256(b"original").hexdigest())


def test_all_source_unit_names_preserved(tmp_path):
    module = preparation()
    import csv

    path = tmp_path / "units.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(module.UNIT_HEADERS)
        writer.writerow(["  Synthetic Unit  "] + ["value"] * 14)
    rows = module.read_units(path)
    assert rows[0]["unit"] == "  Synthetic Unit  "
    assert rows[0]["key"] == "Synthetic Unit"


def test_complete_source_preparation_preserves_exclusion_evidence(reference_bundle, tmp_path):
    import csv
    import json
    from types import SimpleNamespace
    from xml.sax.saxutils import escape
    from zipfile import ZipFile

    from contracts.references import load_directory

    module = preparation()
    units = tmp_path / "unit.csv"
    with units.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(module.UNIT_HEADERS)
        writer.writerow(["School"] + ["Synthetic"] * 14)
    headers = module.JOB_HEADERS
    normal = ["School", "", "Teacher", "Guru", "Main duties\nBatasan\nNot duties", "Synthetic"]
    excluded = ["School", "", "Unreviewed", "Guru", "Excluded duties", "Synthetic"]

    def row(number, values):
        return (
            '<row r="'
            + str(number)
            + '">'
            + "".join(
                f'<c r="{chr(65 + index)}{number}" t="inlineStr"><is>'
                f"<t>{escape(value)}</t></is></c>"
                for index, value in enumerate(values)
            )
            + "</row>"
        )

    jobs = tmp_path / "jobs.xlsx"
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with ZipFile(jobs, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{ns}" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="JABATAN" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship Id="rId1" '
            'Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{ns}"><sheetData>'
            + row(1, headers)
            + row(2, normal)
            + row(210, excluded)
            + "</sheetData></worksheet>",
        )
    manifest = json.loads((reference_bundle / "manifest.json").read_text())
    source = {
        "unit_sha256": sha256(units.read_bytes()).hexdigest(),
        "jobs_sha256": sha256(jobs.read_bytes()).hexdigest(),
        "templates": manifest["templates"],
        "exclusions": [
            {
                "row": 210,
                "key": "School||(Umum)||Unreviewed",
                "sha256": sha256(json.dumps(excluded, ensure_ascii=False).encode()).hexdigest(),
                "reason": "Synthetic reviewed mismatch",
            }
        ],
    }
    source_manifest = tmp_path / "source-manifest.json"
    source_manifest.write_text(json.dumps(source))
    output = tmp_path / "prepared"
    report = module.prepare(
        SimpleNamespace(
            unit_csv=units,
            jobdesk_xlsx=jobs,
            templates_dir=reference_bundle,
            source_manifest=source_manifest,
            output=output,
            version="prepared-v1",
        )
    )
    bundle = load_directory(output, "prepared-v1")
    assert report["units"] == report["jobs"] == 1
    assert report["exclusions"] == source["exclusions"]
    assert bundle.jobs["school||(umum)||teacher"]["jobdesk"] == "Main duties"
    assert sha256(jobs.read_bytes()).hexdigest() == source["jobs_sha256"]
