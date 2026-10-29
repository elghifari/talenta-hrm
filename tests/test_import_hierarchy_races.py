from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from audit.models import AuditEvent
from django.db import OperationalError, connection, transaction
from employees.models import Employee
from employees.serializers import EmployeeSerializer
from organization.models import Branch, Division
from test_employee_import import hr as hr
from test_employee_import import upload
from test_employee_import_concurrency import worker

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("target", ["branch", "division"])
def test_confirmation_locks_reviewed_names_until_employee_and_audit_commit(hr, monkeypatch, target):
    client, _ = hr
    branch = Branch.objects.create(name="Cabang Utama")
    division = Division.objects.create(branch=branch, name="Pelayanan")
    draft = upload(
        client,
        "ID Karyawan,Nama Lengkap,Cabang,Divisi\n0010,Karyawan Hierarki,Cabang Utama,Pelayanan\n",
    ).json()
    entered, release = Event(), Event()
    original = EmployeeSerializer.is_valid

    def hold_validation(serializer, *args, **kwargs):
        entered.set()
        assert release.wait(timeout=20)
        return original(serializer, *args, **kwargs)

    monkeypatch.setattr(EmployeeSerializer, "is_valid", hold_validation)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            worker, client.cookies, f"/api/employees/imports/{draft['id']}/confirm/"
        )
        try:
            assert entered.wait(timeout=20)
            record = branch if target == "branch" else division
            with pytest.raises(OperationalError) as error, transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout = '300ms'")
                type(record).objects.filter(pk=record.pk).update(name="Nama Diubah")
            assert error.value.__cause__.sqlstate == "55P03"
        finally:
            release.set()
        status, result = future.result(timeout=20)
    assert status == 200, result
    employee = Employee.objects.get(employee_code="0010")
    assert (employee.branch_id, employee.division_id) == (branch.pk, division.pk)
    assert AuditEvent.objects.count() == 1
    branch.refresh_from_db()
    division.refresh_from_db()
    assert (branch.name, division.name) == ("Cabang Utama", "Pelayanan")
