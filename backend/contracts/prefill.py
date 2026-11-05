import re

from rest_framework.exceptions import ValidationError

from .constants import UNIT_DEFAULT_FIELDS
from .fields import field_spec


def normalize(value):
    return value.strip().casefold()


def apply_unit_default(bundle, unit_key, pkwt_type):
    row = bundle.units.get(normalize(unit_key))
    if row is None:
        raise ValidationError({"source_unit": ["Unit sumber tidak ditemukan."]})
    allowed = UNIT_DEFAULT_FIELDS & {f["key"] for f in field_spec(pkwt_type)}
    values = {key: value for key, value in row.items() if key in allowed}
    values["nama_unit"] = row["unit"]
    values["kota_ttd"] = "Bogor" if re.search(r"bogor|tcb", row["unit"], re.I) else "Bekasi"
    values["saksi2_jabatan"] = (
        "Kepala " + row["unit"]
        if pkwt_type == "guru"
        else "HR Manager Yayasan Bina Talenta Tunas Bangsa Karya Mandiri"
    )
    return values


def apply_job_default(bundle, job_key, pkwt_type):
    row = bundle.jobs.get(normalize(job_key))
    if row is None or row.get("pkwt_type") != pkwt_type:
        raise ValidationError({"job_default_key": ["Default jabatan tidak sesuai tipe PKWT."]})
    return {"jabatan": row["title"], "jobdesk": row["jobdesk"]}


def prefill_employee(employee, bundle):
    snapshot = {
        key: getattr(employee, key)
        for key in ("employee_code", "full_name", "job_title", "employment_status", "pkwt_type")
    }
    for key in ("date_of_birth", "contract_expiry"):
        value = getattr(employee, key)
        snapshot[key] = value.isoformat() if value else None
    snapshot["branch"] = employee.branch.name if employee.branch else ""
    snapshot["division"] = employee.division.name if employee.division else ""
    values = {
        "nama": employee.full_name,
        "nip": "",
        "jabatan": employee.job_title,
        "tgl_lahir": snapshot["date_of_birth"] or "",
        "tambahan_mode": "tambah",
    }
    unit = next(
        (r for r in bundle.units.values() if normalize(r["unit"]) == normalize(snapshot["branch"])),
        None,
    )
    source_unit, job_key = None, None
    if unit:
        source_unit = unit["key"]
        values.update(apply_unit_default(bundle, source_unit, employee.pkwt_type))
        matches = [
            r
            for r in bundle.jobs.values()
            if normalize(r["unit"]) == normalize(unit["unit"])
            and normalize(r["division"] or "(Umum)") == normalize(snapshot["division"] or "(Umum)")
            and normalize(r["title"]) == normalize(employee.job_title)
            and r["pkwt_type"] == employee.pkwt_type
        ]
        if len(matches) == 1:
            job_key = matches[0]["key"]
            values.update(apply_job_default(bundle, job_key, employee.pkwt_type))
    return {
        "employee_snapshot": snapshot,
        "source_unit": source_unit,
        "job_default_key": job_key,
        "values": values,
    }
