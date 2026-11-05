import argparse
import csv
import json
import re
import shutil
from hashlib import sha256
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET
from zipfile import ZipFile

UNIT_HEADERS = [
    "Unit",
    "Nama Pihak Pertama",
    "Alamat (jalan)",
    "Kelurahan/Desa",
    "Kecamatan",
    "Kabupaten/Kota",
    "Provinsi",
    "Kode Pos",
    "Hari Kerja / Minggu",
    "Rentang Hari Kerja",
    "Jam Kerja / Minggu (tidak dipakai - dihitung otomatis)",
    "Jam Senin-Jumat",
    "Jam Sabtu",
    "Istirahat Senin-Jumat",
    "Istirahat Jumat",
]
UNIT_KEYS = [
    "unit",
    "pihak1_nama",
    "alamat_unit",
    "unit_kelurahan",
    "unit_kecamatan",
    "unit_kota",
    "unit_provinsi",
    "unit_kodepos",
    "hari_kerja_jml",
    "hari_kerja_rentang",
    "jam_minggu_jml__usang",
    "jam_sen_jum",
    "jam_sabtu_jam",
    "jam_ist",
    "jam_ist_jumat",
]
JOB_HEADERS = ["Unit", "Divisi", "Jabatan", "Jenis PKWT", "Jobdesk", "Sumber"]
TYPES = {"Yayasan": "yayasan", "Guru": "guru", "Klinik Umum": "klinik_umum"}
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def verify_source(path, expected):
    if not re.fullmatch(r"[0-9a-f]{64}", expected or ""):
        raise ValueError("Invalid source fingerprint")
    if sha256(Path(path).read_bytes()).hexdigest() != expected:
        raise ValueError("Source fingerprint mismatch")


def read_units(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    if not rows or rows[0] != UNIT_HEADERS:
        raise ValueError("UNIT column order mismatch")
    result, seen = [], set()
    for row in rows[1:]:
        if not any(row):
            continue
        if len(row) != 15 or not row[0].strip():
            raise ValueError("Invalid UNIT row")
        key = row[0].strip()
        if key.casefold() in seen:
            raise ValueError("Duplicate UNIT")
        seen.add(key.casefold())
        result.append({"key": key, **dict(zip(UNIT_KEYS, row, strict=True))})
    return result


def read_job_rows(path):
    with ZipFile(path) as archive:
        if sum(i.file_size for i in archive.infolist()) > 32 * 1024 * 1024:
            raise ValueError("Workbook too large")
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheet = next((s for s in workbook.find("s:sheets", NS) if s.get("name") == "JABATAN"), None)
        if sheet is None:
            raise ValueError("JABATAN sheet missing")
        rid = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(r.get("Target") for r in relations if r.get("Id") == rid)
        member = str(PurePosixPath("xl") / target) if not target.startswith("/") else target[1:]
        if ".." in PurePosixPath(member).parts or not member.startswith("xl/"):
            raise ValueError("Invalid sheet path")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = [
                "".join(s.itertext())
                for s in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("s:si", NS)
            ]
        rows = []
        for row in ET.fromstring(archive.read(member)).findall("s:sheetData/s:row", NS):
            values = [""] * 6
            for cell in row:
                match = re.fullmatch(r"([A-Z]+)[0-9]+", cell.get("r", ""))
                if not match or len(match[1]) != 1 or match[1] > "F":
                    continue
                if cell.find("s:f", NS) is not None:
                    raise ValueError("Formula in job catalog")
                kind = cell.get("t")
                value = cell.findtext("s:v", default="", namespaces=NS)
                if kind == "s":
                    value = strings[int(value)]
                elif kind == "inlineStr":
                    value = "".join(cell.find("s:is", NS).itertext())
                elif value:
                    raise ValueError("Non-text cell in job catalog")
                values[ord(match[1]) - ord("A")] = value
            rows.append((int(row.get("r")), values))
        if not rows or rows[0][1] != JOB_HEADERS:
            raise ValueError("JABATAN headers mismatch")
        return rows[1:]


def prepare(args):
    manifest = json.loads(Path(args.source_manifest).read_text(encoding="utf-8"))
    verify_source(args.unit_csv, manifest["unit_sha256"])
    verify_source(args.jobdesk_xlsx, manifest["jobs_sha256"])
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}", args.version):
        raise ValueError("Invalid version")
    units = read_units(args.unit_csv)
    exclusions = {int(e["row"]): e for e in manifest.get("exclusions", [])}
    jobs, report, used, seen = [], [], set(), set()
    for number, values in read_job_rows(args.jobdesk_xlsx):
        unit, division, title, kind, duties, _ = values
        key = "||".join((unit.strip(), division.strip() or "(Umum)", title.strip()))
        row_digest = sha256(json.dumps(values, ensure_ascii=False).encode("utf-8")).hexdigest()
        if number in exclusions:
            exclusion = exclusions[number]
            if (
                exclusion["key"] != key
                or exclusion["sha256"] != row_digest
                or not exclusion.get("reason")
            ):
                raise ValueError("Exclusion evidence mismatch")
            report.append(exclusion)
            used.add(number)
            continue
        if not unit.strip() or not title.strip():
            continue
        if number in {210, 213, 231, 245}:
            raise ValueError("Required exclusion evidence missing")
        if kind not in TYPES or key.casefold() in seen:
            raise ValueError("Unknown type or duplicate job key")
        seen.add(key.casefold())
        duties = re.split(
            r"(?:^|\n)\s*(?:Batasan|Hubungan Kerja|Persyaratan|Kualifikasi|Kompetensi|"
            r"Sikap/Kepribadian)",
            duties,
            maxsplit=1,
            flags=re.I,
        )[0].strip()
        if not duties or len(duties) > 20000:
            raise ValueError("Empty or oversized duties require explicit exclusion")
        if unit.strip().casefold() not in {u["key"].casefold() for u in units}:
            raise ValueError("Job UNIT missing")
        jobs.append(
            {
                "key": key,
                "unit": unit,
                "division": division,
                "title": title,
                "pkwt_type": TYPES[kind],
                "jobdesk": duties,
                "source_row": str(number),
            }
        )
    if used != set(exclusions):
        raise ValueError("Unused exclusion evidence")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    package = {"version": args.version, "templates": {}}
    for name, data in (("units", units), ("jobs", jobs), ("exclusions", report)):
        path = output / (name + ".json")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if name != "exclusions":
            package[name + "_file"] = path.name
            package[name + "_sha256"] = sha256(path.read_bytes()).hexdigest()
    for kind in TYPES.values():
        template = manifest["templates"][kind]
        source = Path(args.templates_dir) / template["file"]
        if not source.resolve().is_relative_to(Path(args.templates_dir).resolve()):
            raise ValueError("Unsafe template path")
        verify_source(source, template["sha256"])
        destination = output / (kind + ".docx")
        shutil.copyfile(source, destination)
        package["templates"][kind] = {"file": destination.name, "sha256": template["sha256"]}
    (output / "manifest.json").write_text(json.dumps(package, indent=2), encoding="utf-8")
    return {"version": args.version, "units": len(units), "jobs": len(jobs), "exclusions": report}


def main():
    parser = argparse.ArgumentParser()
    for name in (
        "unit-csv",
        "jobdesk-xlsx",
        "templates-dir",
        "source-manifest",
        "output",
        "version",
    ):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args), ensure_ascii=False))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
