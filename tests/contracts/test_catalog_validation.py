import json
from hashlib import sha256

import pytest
from contracts.references import ReferenceUnavailable, load_reference_bundle


@pytest.mark.parametrize("key", ["nama", "nip", "gaji_pokok"])
def test_unit_catalog_cannot_supply_personal_or_salary_fields(reference_bundle, key):
    path = reference_bundle / "units.json"
    rows = json.loads(path.read_text())
    rows[0][key] = "Injected value"
    path.write_text(json.dumps(rows))
    manifest_path = reference_bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["units_sha256"] = sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ReferenceUnavailable):
        load_reference_bundle()


@pytest.mark.parametrize(
    "rows",
    [
        [{"key": "job"}],
        [
            {
                "key": "job",
                "unit": "School",
                "division": "",
                "title": "Title",
                "pkwt_type": "magang",
                "jobdesk": "Duties",
            }
        ],
    ],
)
def test_malformed_job_catalog_fails_closed(reference_bundle, rows):
    path = reference_bundle / "jobs.json"
    path.write_text(json.dumps(rows))
    manifest_path = reference_bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["jobs_sha256"] = sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ReferenceUnavailable):
        load_reference_bundle()
