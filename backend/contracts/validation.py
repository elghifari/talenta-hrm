import re
from datetime import date

from rest_framework.exceptions import ValidationError

from .fields import AMOUNTS, DATES, field_spec
from .formatting import parse_range


def validate_values(pkwt_type, values, *, complete):
    fields = {f["key"]: f for f in field_spec(pkwt_type)}
    if not isinstance(values, dict):
        raise ValidationError({"values": ["Isian harus berupa objek."]})
    errors, result = {}, {}
    for key, value in values.items():
        if key not in fields:
            errors[key] = ["Isian tidak dikenal."]
            continue
        field = fields[key]
        if not isinstance(value, str):
            errors[key] = ["Isian harus berupa teks."]
            continue
        if len(value) > field["max_length"]:
            errors[key] = ["Isian terlalu panjang."]
            continue
        # XML 1.0 cannot represent these controls, even when escaped.
        if any(
            not (
                c in "\t\n\r"
                or 0x20 <= ord(c) <= 0xD7FF
                or 0xE000 <= ord(c) <= 0xFFFD
                or 0x10000 <= ord(c) <= 0x10FFFF
            )
            for c in value
        ):
            errors[key] = ["Karakter tidak didukung."]
            continue
        value = value.strip() if field["kind"] != "textarea" else value
        result[key] = value
        if not value:
            continue
        if field["choices"] and value not in field["choices"]:
            errors[key] = ["Pilihan tidak valid."]
        if key in AMOUNTS or key == "hari_kerja_jml":
            if not re.fullmatch(r"[0-9]{1,15}", value):
                errors[key] = ["Gunakan bilangan bulat nonnegatif."]
            elif key == "hari_kerja_jml" and not 1 <= int(value) <= 7:
                errors[key] = ["Jumlah hari harus 1 sampai 7."]
        if key in DATES:
            try:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                    raise ValueError()
                date.fromisoformat(value)
            except ValueError:
                errors[key] = ["Gunakan tanggal valid YYYY-MM-DD."]
        if key.startswith("jam_"):
            try:
                parse_range(value)
            except ValueError as exc:
                errors[key] = [str(exc)]
    for key, field in fields.items():
        if complete and field["required_for_generation"] and not result.get(key, "").strip():
            errors[key] = ["Wajib diisi sebelum membuat DOCX."]
    if result.get("tgl_mulai") and result.get("tgl_berakhir"):
        if not ({"tgl_mulai", "tgl_berakhir"} & errors.keys()):
            if result["tgl_berakhir"] < result["tgl_mulai"]:
                errors["tgl_berakhir"] = ["Tanggal berakhir mendahului tanggal mulai."]
    if result.get("hari_kerja_jml") and result.get("hari_kerja_rentang"):
        from .formatting import RANGES

        if not ({"hari_kerja_jml", "hari_kerja_rentang"} & errors.keys()):
            if int(result["hari_kerja_jml"]) > len(RANGES[result["hari_kerja_rentang"]]):
                errors["hari_kerja_jml"] = ["Jumlah hari melebihi rentang."]
    if errors:
        raise ValidationError(errors)
    return result
