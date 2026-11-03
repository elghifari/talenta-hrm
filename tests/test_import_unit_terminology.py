import csv
import io

import pytest
from organization.models import Branch, Division
from test_employee_import import hr as hr
from test_employee_import import upload

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("header", ["Unit", "unit", "Cabang", "cabang"])
def test_unit_and_legacy_headers_resolve_the_same_existing_record(hr, header):
    client, _ = hr
    unit = Branch.objects.create(name="Klinik Bekasi")
    Division.objects.create(branch=unit, name="Pelayanan")
    response = upload(
        client, f"ID Karyawan,Nama Lengkap,{header},Divisi\n0010,Contoh,klinik bekasi,Pelayanan\n"
    )
    assert response.status_code == 201
    row = response.json()["rows"][0]
    assert row["status"] == "new", row
    assert row["incoming"]["branch"] == str(unit.pk)


def test_unit_and_legacy_columns_cannot_both_target_the_same_field(hr):
    client, _ = hr
    response = upload(client, "ID Karyawan,Nama Lengkap,Unit,Cabang\n0010,Contoh,A,B\n")
    assert response.status_code == 400


def test_downloaded_template_uses_unit(hr):
    client, _ = hr
    response = client.get("/api/employees/import-template/")
    headers = next(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert "Unit" in headers
    assert "Cabang" not in headers


def test_missing_hierarchy_identifies_names_without_creating_records(hr):
    client, _ = hr
    response = upload(
        client, "ID Karyawan,Nama Lengkap,Unit,Divisi\n0010,Contoh,Unit Baru,Pelayanan\n"
    )
    row = response.json()["rows"][0]
    assert row["status"] == "error"
    assert row["missing_hierarchy"] == [
        {"kind": "branch", "name": "Unit Baru", "branch_name": "Unit Baru"},
        {"kind": "division", "name": "Pelayanan", "branch_name": "Unit Baru"},
    ]
    assert not Branch.objects.exists()
    assert not Division.objects.exists()
