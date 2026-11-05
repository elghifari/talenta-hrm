import pytest
from contracts.fields import field_spec
from contracts.validation import validate_values
from rest_framework.exceptions import ValidationError


@pytest.mark.parametrize("value", ["A\uffffB", "A\ufffeB", "A\ud800B", "A\udfffB"])
def test_xml_invalid_unicode_is_a_field_error_even_for_incomplete_save(value):
    with pytest.raises(ValidationError) as error:
        validate_values("yayasan", {"nama": value}, complete=False)
    assert "nama" in error.value.detail


def test_incomplete_draft_is_allowed():
    assert validate_values("yayasan", {}, complete=False) == {}


@pytest.mark.parametrize(
    "values",
    [
        {"tgl_mulai": "2026-02-30"},
        {"lainnya": "-1"},
        {"lainnya": "1.2"},
        {"lainnya": "1e3"},
        {"nip": True},
        {"nip": []},
        {"unknown": "value"},
        {"jobdesk": "x" * 20001},
        {"tgl_surat": "2026-1-1"},
        {"tgl_mulai": "2026-12-01", "tgl_berakhir": "2026-11-01"},
    ],
)
def test_invalid_values_rejected_even_in_incomplete_draft(values):
    with pytest.raises(ValidationError):
        validate_values("yayasan", values, complete=False)


def test_nip_and_explicit_zero_are_preserved():
    result = validate_values("yayasan", {"nip": "0000123", "lainnya": "0"}, complete=False)
    assert result == {"nip": "0000123", "lainnya": "0"}


def test_generation_requires_printed_fields():
    with pytest.raises(ValidationError) as error:
        validate_values("yayasan", {}, complete=True)
    assert "nip" in error.value.detail
    assert "jam_sabtu_jam" not in error.value.detail
    assert "tambahan_text" not in error.value.detail


def test_guru_omits_expertise_and_obsolete_inputs():
    keys = {f["key"] for f in field_spec("guru")}
    assert not keys & {"kepala_unit", "tunj_nikah", "tunj_melahirkan", "bidang_keahlian"}
