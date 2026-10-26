from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from django.db import connections
from django.test import Client
from employees.models import Employee
from employees.serializers import EmployeeSerializer
from organization.models import Branch, Division
from test_employee_grouping import hr as hr


@pytest.mark.django_db(transaction=True)
def test_competing_group_patches_cannot_commit_a_mismatched_branch_division(hr, monkeypatch):
    client, _ = hr
    owner = Branch.objects.create(name="KURI")
    other = Branch.objects.create(name="Sekolah")
    division = Division.objects.create(name="Marketing", branch=owner)
    record = Employee.objects.create(
        employee_code="0007", full_name="Synthetic Employee", branch=owner
    )
    branch_validated, division_validated, release_branch = Event(), Event(), Event()
    original = EmployeeSerializer.is_valid

    def synchronize(serializer, *args, **kwargs):
        result = original(serializer, *args, **kwargs)
        if "branch" in serializer.initial_data:
            branch_validated.set()
            assert release_branch.wait(timeout=15)
        else:
            division_validated.set()
        return result

    monkeypatch.setattr(EmployeeSerializer, "is_valid", synchronize)

    def patch(data):
        connections.close_all()
        try:
            worker = Client()
            worker.cookies = client.cookies.copy()
            return worker.patch(
                f"/api/employees/{record.pk}/", data, content_type="application/json"
            ).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        changing_branch = pool.submit(patch, {"branch": str(other.pk)})
        try:
            assert branch_validated.wait(timeout=10)
            changing_division = pool.submit(patch, {"division": str(division.pk)})
            if division_validated.wait(timeout=1):
                changing_division.result(timeout=10)
        finally:
            release_branch.set()
        statuses = [changing_branch.result(timeout=10), changing_division.result(timeout=10)]
    assert sorted(statuses) == [200, 400]
    record.refresh_from_db()
    assert record.division_id is None or record.division.branch_id == record.branch_id
