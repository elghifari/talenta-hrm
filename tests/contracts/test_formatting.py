import json
from pathlib import Path

import pytest
from contracts.formatting import compose_duties, compose_schedule

CASES = json.loads((Path(__file__).parent / "fixtures/legacy_schedule_cases.json").read_text())


@pytest.mark.parametrize("case", CASES)
def test_exact_supplied_engine_schedule_parity(case):
    assert compose_schedule(case["input"]) == case["expected"]


@pytest.mark.parametrize(
    "mode,extra,main,additional",
    [
        (
            "tambah",
            "Extra",
            "Main\nExtra",
            "Tidak ada, kecuali ditetapkan kemudian sesuai ayat 2 Pasal ini.",
        ),
        (
            "ganti",
            "Extra",
            "Extra",
            "Tidak ada, kecuali ditetapkan kemudian sesuai ayat 2 Pasal ini.",
        ),
        ("pasal3", "Extra", "Main", "Extra"),
        ("ganti", "  ", "Main", "Tidak ada, kecuali ditetapkan kemudian sesuai ayat 2 Pasal ini."),
    ],
)
def test_duty_mode_parity(mode, extra, main, additional):
    assert compose_duties("Main", mode, extra) == {
        "uraian_tugas": main,
        "tugas_tambahan": additional,
    }


def test_additional_duties_are_separate_without_changing_main():
    result = compose_duties("Utama", "pasal3", "Tambahan")
    assert result["uraian_tugas"] == "Utama"
    assert result["tugas_tambahan"] == "Tambahan"


def test_saturday_blank_uses_same_hours_when_saturday_is_working():
    result = compose_schedule(
        {
            "hari_kerja_jml": "6",
            "hari_kerja_rentang": "Senin - Sabtu",
            "jam_sen_jum": "08.00-17.00",
            "jam_sabtu_jam": "",
            "jam_ist": "12.00-13.00",
            "jam_ist_jumat": "11.30-13.00",
        }
    )
    assert result["jam_minggu"] == "54 (lima puluh empat) jam"
