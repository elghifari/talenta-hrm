from types import SimpleNamespace

from contracts.prefill import prefill_employee


def employee(branch="Unmatched"):
    return SimpleNamespace(
        id="synthetic-id",
        employee_code="00042",
        full_name="Synthetic Name",
        date_of_birth=None,
        job_title="Teacher",
        employment_status="kontrak",
        pkwt_type="yayasan",
        contract_expiry=None,
        branch=SimpleNamespace(name=branch),
        division=None,
    )


def test_nip_is_not_employee_code_and_unmatched_unit_stays_empty(reference_bundle):
    from contracts.references import load_reference_bundle

    result = prefill_employee(employee(), load_reference_bundle())
    assert result["values"]["nip"] == ""
    assert result["employee_snapshot"]["employee_code"] == "00042"
    assert result["source_unit"] is None
    assert result["job_default_key"] is None


def test_exact_trimmed_case_insensitive_unit_match(reference_bundle):
    from contracts.references import load_reference_bundle

    result = prefill_employee(employee(" school "), load_reference_bundle())
    assert result["source_unit"] == "School"
    assert result["values"]["pihak1_nama"] == "Synthetic Foundation"


def test_default_job_requires_same_unit_division_type_and_unambiguous_title(reference_bundle):
    from dataclasses import replace

    from contracts.references import load_reference_bundle

    original = load_reference_bundle()
    person = employee("School")
    row = {
        "key": "School||(Umum)||Teacher",
        "unit": "School",
        "division": "",
        "title": "Teacher",
        "pkwt_type": "yayasan",
        "jobdesk": "Synthetic duties",
    }
    for changed in [{"unit": "Other"}, {"division": "Other"}, {"pkwt_type": "guru"}]:
        bundle = replace(original, jobs={"job": {**row, **changed}})
        assert prefill_employee(person, bundle)["job_default_key"] is None
    ambiguous = replace(original, jobs={"a": row, "b": {**row, "key": "other"}})
    assert prefill_employee(person, ambiguous)["job_default_key"] is None
    matched = replace(original, jobs={row["key"].casefold(): row})
    before = dict(person.__dict__)
    result = prefill_employee(person, matched)
    assert result["values"]["jobdesk"] == "Synthetic duties"
    assert person.__dict__ == before
    assert row["jobdesk"] == "Synthetic duties"


def test_unit_prefill_allowlist_independently_excludes_identity_and_money(reference_bundle):
    from dataclasses import replace

    from contracts.prefill import apply_unit_default
    from contracts.references import load_reference_bundle

    bundle = load_reference_bundle()
    row = {
        "key": "School",
        "unit": "School",
        "pihak1_nama": "Foundation",
        "nama": "Catalog Name",
        "nip": "001234",
        "gaji_pokok": "9000000",
    }
    result = apply_unit_default(replace(bundle, units={"school": row}), "School", "yayasan")
    assert not {"nama", "nip", "gaji_pokok"} & result.keys()
    assert result["pihak1_nama"] == "Foundation"
    assert result["saksi2_jabatan"].startswith("HR Manager")
