import pytest
from audit.models import AuditEvent
from employees.models import Employee
from organization.models import Branch, Division
from test_employee_import import hr as hr
from test_employee_import import upload

pytestmark = pytest.mark.django_db


def test_import_resolves_division_within_named_branch_and_persists_ids(hr):
    client, user = hr
    first = Branch.objects.create(name="Cabang Utama")
    second = Branch.objects.create(name="Cabang Kedua")
    division = Division.objects.create(branch=first, name="Pelayanan")
    Division.objects.create(branch=second, name="Pelayanan")
    response = upload(
        client,
        "ID Karyawan,Nama Lengkap,Cabang,Divisi\n"
        "0010,Karyawan Hierarki, cabang utama , PELAYANAN \n",
    )
    assert response.status_code == 201, response.content
    draft = response.json()
    row = draft["rows"][0]
    assert row["status"] == "new", row
    assert row["incoming"]["branch"] == str(first.pk)
    assert row["incoming"]["division"] == str(division.pk)
    assert row["incoming"]["branch_name"] == first.name
    assert row["incoming"]["division_name"] == division.name
    assert not Employee.objects.exists()
    endpoint = f"/api/employees/imports/{draft['id']}/confirm/"
    result = client.post(endpoint, {}, content_type="application/json")
    assert result.status_code == 200, result.content
    employee = Employee.objects.get(employee_code="0010")
    assert (employee.branch_id, employee.division_id) == (first.pk, division.pk)
    event = AuditEvent.objects.get()
    assert (event.actor_id, event.action, event.target_id) == (
        user.pk,
        "employee.created",
        employee.pk,
    )
    assert client.post(endpoint, {}, content_type="application/json").json() == result.json()
    assert Employee.objects.count() == 1
    assert AuditEvent.objects.count() == 1


@pytest.mark.parametrize(
    "change",
    ["branch_name", "division_name", "division_deleted", "branch_deleted", "division_moved"],
)
def test_confirmation_rejects_changed_hierarchy_without_partial_writes(hr, change):
    client, _ = hr
    branch = Branch.objects.create(name="Cabang Utama")
    division = Division.objects.create(branch=branch, name="Pelayanan")
    draft = upload(
        client,
        "ID Karyawan,Nama Lengkap,Cabang,Divisi\n"
        "0010,Karyawan Tanpa Cabang,,\n0011,Karyawan Hierarki,Cabang Utama,Pelayanan\n",
    ).json()
    assert draft["summary"]["error"] == 0
    if change == "branch_name":
        Branch.objects.filter(pk=branch.pk).update(name="Cabang Diubah")
    elif change == "division_name":
        Division.objects.filter(pk=division.pk).update(name="Divisi Diubah")
    elif change == "division_deleted":
        division.delete()
    elif change == "branch_deleted":
        division.delete()
        branch.delete()
    else:
        other = Branch.objects.create(name="Cabang Lain")
        Division.objects.filter(pk=division.pk).update(branch=other)
    result = client.post(
        f"/api/employees/imports/{draft['id']}/confirm/", {}, content_type="application/json"
    )
    assert result.status_code == 409, result.content
    assert not Employee.objects.exists()
    assert not AuditEvent.objects.exists()
    assert client.get(f"/api/employees/imports/{draft['id']}/").json()["state"] == "pending"


@pytest.mark.parametrize(
    ("branch_name", "division_name", "error_field"),
    [
        ("Tidak Ada", "", "branch"),
        ("Cabang Utama", "Tidak Ada", "division"),
        ("", "Pelayanan", "division"),
        ("Cabang Lain", "Pelayanan", "division"),
    ],
)
def test_unknown_or_cross_branch_names_block_the_whole_batch(
    hr, branch_name, division_name, error_field
):
    client, _ = hr
    branch = Branch.objects.create(name="Cabang Utama")
    Branch.objects.create(name="Cabang Lain")
    Division.objects.create(branch=branch, name="Pelayanan")
    draft = upload(
        client,
        "ID Karyawan,Nama Lengkap,Cabang,Divisi\n"
        "0010,Karyawan Valid,Cabang Utama,Pelayanan\n"
        f"0011,Karyawan Invalid,{branch_name},{division_name}\n",
    ).json()
    assert draft["rows"][1]["status"] == "error"
    assert error_field in draft["rows"][1]["errors"]
    result = client.post(
        f"/api/employees/imports/{draft['id']}/confirm/", {}, content_type="application/json"
    )
    assert result.status_code == 400
    assert not Employee.objects.exists()
    assert not AuditEvent.objects.exists()
    assert Branch.objects.count() == 2
    assert Division.objects.count() == 1


@pytest.mark.parametrize(
    "headers,values",
    [("", ""), (",Cabang,Divisi", ",,"), (",Cabang,Divisi", ",cabang utama,PELAYANAN")],
)
def test_missing_blank_or_equivalent_hierarchy_cells_preserve_assignments(hr, headers, values):
    client, _ = hr
    branch = Branch.objects.create(name="Cabang Utama")
    division = Division.objects.create(branch=branch, name="Pelayanan")
    employee = Employee.objects.create(
        employee_code="0010", full_name="Karyawan Lama", branch=branch, division=division
    )
    draft = upload(
        client, f"ID Karyawan,Nama Lengkap{headers}\n0010,Karyawan Lama{values}\n"
    ).json()
    row = draft["rows"][0]
    assert row["status"] == "unchanged", row
    assert row["incoming"]["branch_name"] == branch.name
    assert row["incoming"]["division_name"] == division.name
    assert not row["changes"]
    result = client.post(
        f"/api/employees/imports/{draft['id']}/confirm/", {}, content_type="application/json"
    )
    assert result.status_code == 200
    employee.refresh_from_db()
    assert (employee.branch_id, employee.division_id) == (branch.pk, division.pk)
    assert not AuditEvent.objects.exists()


def test_import_updates_hierarchy_only_with_reviewed_valid_pair(hr):
    client, _ = hr
    first = Branch.objects.create(name="Cabang Lama")
    second = Branch.objects.create(name="Cabang Baru")
    old = Division.objects.create(branch=first, name="Pelayanan")
    new = Division.objects.create(branch=second, name="Pelayanan")
    employee = Employee.objects.create(
        employee_code="0010", full_name="Karyawan Lama", branch=first, division=old
    )
    draft = upload(
        client, "ID Karyawan,Nama Lengkap,Cabang,Divisi\n0010,Karyawan Lama,Cabang Baru,Pelayanan\n"
    ).json()
    row = draft["rows"][0]
    assert row["status"] == "update"
    assert set(row["changes"]) == {"branch", "division"}
    assert row["current"]["branch_name"] == first.name
    assert row["incoming"]["branch_name"] == second.name
    assert (
        client.post(
            f"/api/employees/imports/{draft['id']}/confirm/", {}, content_type="application/json"
        ).status_code
        == 200
    )
    employee.refresh_from_db()
    assert (employee.branch_id, employee.division_id) == (second.pk, new.pk)
    assert AuditEvent.objects.get().action == "employee.updated"


def test_division_only_uses_existing_branch_but_branch_change_cannot_silently_clear_division(hr):
    client, _ = hr
    first = Branch.objects.create(name="Cabang Lama")
    Branch.objects.create(name="Cabang Baru")
    old = Division.objects.create(branch=first, name="Pelayanan")
    new = Division.objects.create(branch=first, name="Administrasi")
    employee = Employee.objects.create(
        employee_code="0010", full_name="Karyawan Lama", branch=first, division=old
    )
    invalid = upload(
        client, "ID Karyawan,Nama Lengkap,Cabang,Divisi\n0010,Karyawan Lama,Cabang Baru,\n"
    ).json()
    assert invalid["rows"][0]["status"] == "error"
    draft = upload(
        client, "ID Karyawan,Nama Lengkap,Divisi\n0010,Karyawan Lama,Administrasi\n"
    ).json()
    assert draft["rows"][0]["status"] == "update"
    assert draft["rows"][0]["changes"] == ["division"]
    assert (
        client.post(
            f"/api/employees/imports/{draft['id']}/confirm/", {}, content_type="application/json"
        ).status_code
        == 200
    )
    employee.refresh_from_db()
    assert (employee.branch_id, employee.division_id) == (first.pk, new.pk)
