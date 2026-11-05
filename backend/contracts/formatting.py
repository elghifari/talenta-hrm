import re
from datetime import date

from rest_framework.exceptions import ValidationError

from .constants import TOKENS

MONTHS = (
    "Januari Februari Maret April Mei Juni Juli Agustus September Oktober November Desember".split()
)
ROMAN = "I II III IV V VI VII VIII IX X XI XII".split()


def date_words(value):
    parsed = date.fromisoformat(value)
    return f"{parsed.day} {MONTHS[parsed.month - 1]} {parsed.year}"


def compile_tokens(pkwt_type, values):
    from .fields import AMOUNTS
    from .validation import validate_values

    values = validate_values(pkwt_type, values, complete=True)
    result = {key: values.get(key, "") for key in TOKENS[pkwt_type]}
    result.update(
        compose_duties(
            values["jobdesk"],
            values.get("tambahan_mode", "tambah"),
            values.get("tambahan_text", ""),
        )
    )
    result.update(compose_schedule(values))
    for key in AMOUNTS:
        result[key] = "Rp " + f"{int(values[key]):,}".replace(",", ".")
    for key in ("tgl_lahir", "tgl_mulai", "tgl_berakhir"):
        result[key] = date_words(values[key])
    signing = date.fromisoformat(values["tgl_surat"])
    result.update(
        hari=DAYS[signing.weekday()],
        tgl_surat_teks=date_words(values["tgl_surat"]),
        bulan_romawi=ROMAN[signing.month - 1],
        tahun=str(signing.year),
    )
    return {key: result[key] for key in TOKENS[pkwt_type]}


NUMBERS = "nol satu dua tiga empat lima enam tujuh delapan sembilan sepuluh sebelas".split()
DAYS = "Senin Selasa Rabu Kamis Jumat Sabtu Minggu".split()
RANGES = {"Senin - Jumat": DAYS[:5], "Senin - Sabtu": DAYS[:6], "Senin - Minggu": DAYS}
EMPTY_DUTIES = "Tidak ada, kecuali ditetapkan kemudian sesuai ayat 2 Pasal ini."


def number_words(value):
    if value < 0 or value > 99:
        return str(value)
    if value < 12:
        return NUMBERS[value]
    if value < 20:
        return NUMBERS[value - 10] + " belas"
    return NUMBERS[value // 10] + " puluh" + (" " + NUMBERS[value % 10] if value % 10 else "")


def compose_duties(jobdesk, mode, extra):
    result = {"uraian_tugas": jobdesk, "tugas_tambahan": EMPTY_DUTIES}
    extra = extra.strip()
    if extra:
        if mode == "ganti":
            result["uraian_tugas"] = extra
        elif mode == "pasal3":
            result["tugas_tambahan"] = extra
        else:
            result["uraian_tugas"] = jobdesk + "\n" + extra
    return result


def parse_time(value):
    value = re.sub(r"\s*wib\s*$", "", value.strip(), flags=re.I)
    match = re.fullmatch(r"(\d{1,2})(?:[.:](\d{2}))?", value, flags=re.ASCII)
    if not match:
        match = re.fullmatch(r"(\d{2})(\d{2})", value, flags=re.ASCII)
    if not match:
        raise ValueError("Format jam tidak valid.")
    hour, minute = int(match[1]), int(match[2] or 0)
    if hour > 23 or minute > 59:
        raise ValueError("Jam di luar rentang.")
    return hour * 60 + minute


def parse_range(value):
    parts = [
        p
        for p in re.split(
            r"\s*(?:-|\u2013|\u2014|s/d|s\.d\.|sd|sampai(?:\s+dengan)?)\s*",
            value.strip(),
            flags=re.I,
        )
        if p
    ]
    if len(parts) != 2:
        raise ValueError("Isi dua jam, misalnya 08.00-16.00.")
    return tuple(parse_time(p) for p in parts)


def time_words(value):
    hour, minute = divmod(value, 60)
    return (
        f"{hour:02}.{minute:02} ({number_words(hour)} titik "
        + ("nol nol" if minute == 0 else number_words(minute))
        + ")"
    )


def duration(value):
    hours, minutes = divmod(value, 60)
    return f"{hours} ({number_words(hours)}) jam" + (
        f" {minutes} ({number_words(minutes)}) menit" if minutes else ""
    )


def span(pair):
    value = pair[1] - pair[0]
    return value + 1440 if value < 0 else value


def compose_schedule(values):
    try:
        count = int(values["hari_kerja_jml"])
        days = RANGES[values["hari_kerja_rentang"]]
        if not 1 <= count <= len(days):
            raise ValueError("Jumlah hari tidak sesuai rentang.")
    except (ValueError, KeyError) as exc:
        raise ValidationError({"hari_kerja_jml": ["Jumlah/rentang hari tidak valid."]}) from exc
    pairs = {}
    for key in ("jam_sen_jum", "jam_ist", "jam_ist_jumat", "jam_sabtu_jam"):
        try:
            pairs[key] = parse_range(values[key]) if values.get(key, "").strip() else None
            if key != "jam_sabtu_jam" and pairs[key] is None:
                raise ValueError("Jam wajib diisi.")
        except ValueError as exc:
            raise ValidationError({key: [str(exc)]}) from exc
    weekdays = pairs["jam_sen_jum"]
    saturday_working = "Sabtu" in days
    saturday = pairs["jam_sabtu_jam"] or (weekdays if saturday_working else None)
    weekday_clause = (
        "Hari Senin sampai dengan hari Jumat berlangsung mulai pukul "
        + time_words(weekdays[0])
        + " sampai dengan pukul "
        + time_words(weekdays[1])
        + "."
    )
    saturday_clause = (
        "Hari Sabtu berlangsung mulai pukul "
        + time_words(saturday[0])
        + " sampai dengan pukul "
        + time_words(saturday[1])
        if saturday
        else "Hari Sabtu merupakan hari libur kerja"
    )
    weekly = (
        (count - 1) * span(weekdays) + span(saturday)
        if saturday_working and count == len(days)
        else count * span(weekdays)
    )
    day_clause = (
        f"{count} ({number_words(count)}) hari yaitu : " + ", ".join(days)
        if count == len(days)
        else f"{count} ({number_words(count)}) hari kerja dalam rentang hari {days[0]} "
        f"sampai dengan hari {days[-1]}, sesuai jadwal kerja yang ditetapkan Perusahaan"
    )
    rest, friday = pairs["jam_ist"], pairs["jam_ist_jumat"]
    return {
        "jam_minggu": duration(weekly),
        "hari_kerja": day_clause,
        "jam_hari": duration(span(weekdays)),
        "jam_senin_jumat": weekday_clause,
        "jam_sabtu": saturday_clause,
        "jam_gabungan": (
            "Hari Senin sampai dengan hari Sabtu berlangsung mulai pukul "
            + time_words(weekdays[0])
            + " sampai dengan pukul "
            + time_words(weekdays[1])
            + "."
            if saturday == weekdays
            else weekday_clause + " " + saturday_clause + "."
        ),
        "istirahat_senin_jumat": "Hari Senin sampai dengan hari Jumat berlangsung pukul "
        + time_words(rest[0])
        + " sampai dengan pukul "
        + time_words(rest[1])
        + ".",
        "istirahat_jumat": "Hari Jumat pukul "
        + time_words(friday[0])
        + " sampai dengan pukul "
        + time_words(friday[1])
        + ".",
    }
