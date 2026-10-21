import csv
import io
from collections import Counter

from rest_framework.exceptions import ValidationError

from .models import Employee
from .serializers import EmployeeSerializer

COLUMNS = {
    "ID Karyawan": "employee_code",
    "Nama Lengkap": "full_name",
    "Tanggal Lahir": "date_of_birth",
    "Jabatan": "job_title",
    "Level": "level",
    "Tanggal Masuk": "start_date",
    "Kontrak Berakhir": "contract_expiry",
}
FIELDS = tuple(COLUMNS.values())
MAX_BYTES = 1024 * 1024
MAX_ROWS = 500


def snapshot(employee):
    if employee is None:
        return None
    return {
        "id": str(employee.pk),
        **{
            key: value.isoformat() if hasattr(value, "isoformat") else value
            for key in FIELDS
            for value in [getattr(employee, key)]
        },
    }


def normalize_header(value):
    name = " ".join(value.strip().lower().split())
    return "tanggal lahir" if name == "ttl" else name


def parse_rows(upload, request):
    if not upload.name.lower().endswith(".csv") or upload.size > MAX_BYTES:
        raise ValidationError({"file": ["Gunakan CSV UTF-8 berukuran maksimal 1 MiB."]})
    try:
        text = upload.read(MAX_BYTES + 1).decode("utf-8-sig")
        if len(text.encode("utf-8")) > MAX_BYTES or "\x00" in text:
            raise ValueError
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        headers = [normalize_header(value) for value in next(reader)]
        mapping = {normalize_header(label): key for label, key in COLUMNS.items()}
        if (
            len(headers) != len(set(headers))
            or not {"id karyawan", "nama lengkap"}.issubset(headers)
            or set(headers) - mapping.keys()
        ):
            raise ValidationError(
                {
                    "file": [
                        "Nama kolom tidak valid atau berulang. "
                        "Gunakan template CSV; urutan kolom bebas."
                    ]
                }
            )
        inputs = []
        previous_line = reader.line_num
        for cells in reader:
            row_number = previous_line + 1
            previous_line = reader.line_num
            if not cells or not any(value.strip() for value in cells):
                continue
            if len(inputs) >= MAX_ROWS:
                raise ValidationError({"file": ["CSV maksimal 500 baris karyawan."]})
            if len(cells) != len(headers):
                raise ValidationError(
                    {"file": [f"Jumlah kolom tidak sesuai pada baris {row_number}."]}
                )
            inputs.append(
                (
                    row_number,
                    {
                        mapping[key]: value.strip()
                        for key, value in zip(headers, cells, strict=True)
                    },
                )
            )
    except (UnicodeError, csv.Error, ValueError, StopIteration) as error:
        raise ValidationError(
            {"file": ["CSV tidak dapat dibaca. Gunakan UTF-8 dan pemisah koma."]}
        ) from error
    if not inputs:
        raise ValidationError({"file": ["CSV belum berisi baris karyawan."]})
    codes = Counter(data.get("employee_code", "") for _, data in inputs)
    records = {
        record.employee_code: record for record in Employee.objects.filter(employee_code__in=codes)
    }
    rows = []
    for row_number, raw in inputs:
        code = raw.get("employee_code", "")
        employee = records.get(code)
        current = snapshot(employee)
        data = {
            key: value
            for key, value in raw.items()
            if value or key in {"employee_code", "full_name"}
        }
        serializer = EmployeeSerializer(
            employee, data=data, partial=employee is not None, context={"request": request}
        )
        serializer.is_valid()
        errors = {
            key: [str(value) for value in values] for key, values in serializer.errors.items()
        }
        if codes[code] > 1:
            errors["employee_code"] = ["ID Karyawan berulang dalam CSV."]
        defaults = {
            key: None if key in {"date_of_birth", "start_date", "contract_expiry"} else ""
            for key in FIELDS
        }
        normalized = (
            data
            if errors
            else {
                key: value.isoformat() if hasattr(value, "isoformat") else value
                for key, value in serializer.validated_data.items()
            }
        )
        incoming = {**(current or defaults), **normalized}
        incoming.pop("id", None)
        changes = [
            key
            for key in FIELDS
            if key != "employee_code" and (current is None or current[key] != incoming[key])
        ]
        status = (
            "error"
            if errors
            else "new"
            if current is None
            else "update"
            if changes
            else "unchanged"
        )
        rows.append(
            {
                "row": row_number,
                "employee_code": code,
                "full_name": incoming["full_name"],
                "status": status,
                "current": current,
                "incoming": incoming,
                "changes": changes,
                "errors": errors,
            }
        )
    return rows


def summarize(rows):
    return {
        status: sum(row["status"] == status for row in rows)
        for status in ("new", "update", "unchanged", "error")
    }
