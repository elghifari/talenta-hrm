from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from audit.models import AuditEvent
from django.db import connections
from django.test import Client
from employees.models import Employee, EmployeeImportBatch
from employees.serializers import EmployeeSerializer
from test_employee_import import existing as existing
from test_employee_import import hr as hr
from test_employee_import import mixed_csv, upload

pytestmark = pytest.mark.django_db(transaction=True)


def worker(cookies, endpoint, barrier=None):
    connections.close_all()
    try:
        client = Client()
        client.cookies = cookies.copy()
        if barrier:
            barrier.wait(timeout=20)
        response = client.post(endpoint, {}, content_type="application/json")
        return response.status_code, response.json()
    finally:
        connections.close_all()


def test_parallel_confirmations_return_one_receipt(hr, existing):
    client, _ = hr
    draft = upload(client, mixed_csv()).json()
    endpoint = f"/api/employees/imports/{draft['id']}/confirm/"
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, client.cookies, endpoint, barrier) for _ in range(2)]
        results = [future.result(timeout=40) for future in futures]
    assert results[0] == results[1]
    assert results[0][0] == 200
    assert Employee.objects.count() == 4
    assert AuditEvent.objects.count() == 2


def test_competing_new_codes_have_one_winner_and_no_partial_audit(hr, monkeypatch):
    client, _ = hr
    drafts = [
        upload(client, "ID Karyawan,Nama Lengkap\n0088,Concurrent CSV\n").json() for _ in range(2)
    ]
    barrier = Barrier(2)
    original = EmployeeSerializer.is_valid

    def validate_together(serializer, *args, **kwargs):
        result = original(serializer, *args, **kwargs)
        barrier.wait(timeout=20)
        return result

    monkeypatch.setattr(EmployeeSerializer, "is_valid", validate_together)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(worker, client.cookies, f"/api/employees/imports/{draft['id']}/confirm/")
            for draft in drafts
        ]
        results = [future.result(timeout=40) for future in futures]
    assert sorted(status for status, _ in results) == [200, 409]
    assert Employee.objects.filter(employee_code="0088").count() == 1
    assert AuditEvent.objects.count() == 1
    assert EmployeeImportBatch.objects.filter(result__isnull=False).count() == 1
    assert EmployeeImportBatch.objects.filter(result__isnull=True).count() == 1
