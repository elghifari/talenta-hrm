import json
from hashlib import sha256
from io import BytesIO

import pytest
from docx import Document


@pytest.fixture
def reference_bundle(settings, tmp_path):
    root = tmp_path / "references"
    directory = root / "synthetic-v1"
    directory.mkdir(parents=True)
    templates = {}
    for kind in ("yayasan", "guru", "klinik_umum"):
        doc = Document()
        doc.add_paragraph("Synthetic " + kind)
        paragraph = doc.add_paragraph()
        paragraph.add_run("{{na")
        paragraph.add_run("ma}}")
        from contracts.constants import TOKENS

        for key in sorted(TOKENS[kind] - {"nama", "uraian_tugas"}):
            doc.add_paragraph("{{" + key + "}}")
        doc.add_table(rows=1, cols=1).cell(0, 0).add_table(rows=1, cols=1).cell(
            0, 0
        ).text = "{{uraian_tugas}}"
        doc.sections[0].footer.paragraphs[0].text = "Synthetic footer"
        stream = BytesIO()
        doc.save(stream)
        name = kind + ".docx"
        (directory / name).write_bytes(stream.getvalue())
        templates[kind] = {"file": name, "sha256": sha256(stream.getvalue()).hexdigest()}
    units = [{"key": "School", "unit": "School", "pihak1_nama": "Synthetic Foundation"}]
    for name, data in (("units", units), ("jobs", [])):
        (directory / (name + ".json")).write_text(json.dumps(data), encoding="utf-8")
    manifest = {"version": "synthetic-v1", "templates": templates}
    for name in ("units", "jobs"):
        manifest[name + "_file"] = name + ".json"
        manifest[name + "_sha256"] = sha256((directory / (name + ".json")).read_bytes()).hexdigest()
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "active.json").write_text(json.dumps({"version": "synthetic-v1"}))
    settings.CONTRACT_REFERENCE_ROOT = root
    return directory


@pytest.fixture
def contract_values():
    from contracts.fields import AMOUNTS, field_spec

    values = {f["key"]: "Synthetic text" for f in field_spec("yayasan")}
    values.update({key: "0" for key in AMOUNTS})
    values.update(
        {
            "tgl_surat": "2026-11-05",
            "tgl_lahir": "1995-01-01",
            "tgl_mulai": "2026-12-01",
            "tgl_berakhir": "2027-11-30",
            "nip": "0000123",
            "jenis_kelamin": "Perempuan",
            "hari_kerja_jml": "6",
            "hari_kerja_rentang": "Senin - Sabtu",
            "jam_sen_jum": "08.00-17.00",
            "jam_sabtu_jam": "",
            "jam_ist": "12.00-13.00",
            "jam_ist_jumat": "11.30-13.00",
            "tambahan_mode": "pasal3",
            "tambahan_text": "",
            "jangka_waktu": "12 (dua belas) bulan",
        }
    )
    return values


@pytest.fixture
def hr_user(django_user_model):
    from django.contrib.auth.models import Group

    user = django_user_model.objects.create_user(email="contract-hr@example.test")
    user.groups.add(Group.objects.get_or_create(name="HR")[0])
    return user


@pytest.fixture
def hr_client(hr_user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(hr_user)
    return client


@pytest.fixture
def employee():
    from employees.models import Employee

    return Employee.objects.create(
        employee_code="00042",
        full_name="Synthetic Employee",
        employment_status="kontrak",
        pkwt_type="yayasan",
    )
