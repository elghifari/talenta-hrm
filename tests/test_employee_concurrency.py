from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.db import IntegrityError, connection, connections
from django.test import Client
from employees.models import Employee
from employees.serializers import EmployeeSerializer

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def hr(django_user_model):
    assert connection.vendor == "postgresql"
    assert connection.settings_dict["NAME"].startswith("test_")
    user = django_user_model.objects.create_user(email="hr-concurrency@example.test")
    user.groups.add(Group.objects.create(name="HR"))
    return user


@pytest.fixture
def synchronized_validation(monkeypatch):
    barrier = Barrier(2, timeout=20)
    original = EmployeeSerializer.is_valid
    loaded = []

    def is_valid(serializer, *args, **kwargs):
        result = original(serializer, *args, **kwargs)
        if result:
            instance = serializer.instance
            loaded.append(
                (instance.pk, instance.employee_code, instance.full_name) if instance else None
            )
            # Both requests finish real validation before either database write.
            barrier.wait()
        return result

    monkeypatch.setattr(EmployeeSerializer, "is_valid", is_valid)
    return loaded


def concurrent_requests(hr, requests):
    def send(request):
        connections.close_all()
        try:
            client = Client(raise_request_exception=False)
            client.force_login(hr)
            method, url, data = request
            return getattr(client, method)(url, data, content_type="application/json")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(send, requests))


def test_simultaneous_creates_return_field_error_for_duplicate_code(hr, synchronized_validation):
    responses = concurrent_requests(
        hr,
        [
            ("post", "/api/employees/", {"employee_code": "RACE", "full_name": name})
            for name in ("Synthetic First", "Synthetic Second")
        ],
    )

    assert synchronized_validation == [None, None]
    assert sorted(response.status_code for response in responses) == [201, 400]
    rejected = next(response for response in responses if response.status_code == 400)
    assert rejected.json() == {
        "employee_code": ["employee with this employee code already exists."]
    }
    employee = Employee.objects.get()
    winner = next(response for response in responses if response.status_code == 201)
    assert winner.json()["id"] == str(employee.pk)
    event = AuditEvent.objects.get()
    assert (event.action, event.target_id, event.actor_id) == (
        "employee.created",
        employee.pk,
        hr.pk,
    )


def test_simultaneous_code_patches_return_field_error_for_duplicate_code(
    hr, synchronized_validation
):
    employees = [
        Employee.objects.create(employee_code=code, full_name=f"Synthetic {code}")
        for code in ("FIRST", "SECOND")
    ]
    originals = {
        employee.pk: (employee.employee_code, employee.full_name) for employee in employees
    }
    responses = concurrent_requests(
        hr,
        [
            ("patch", f"/api/employees/{employee.pk}/", {"employee_code": "RACE"})
            for employee in employees
        ],
    )

    assert set(synchronized_validation) == {
        (employee.pk, *originals[employee.pk]) for employee in employees
    }
    assert sorted(response.status_code for response in responses) == [200, 400]
    rejected = next(response for response in responses if response.status_code == 400)
    assert rejected.json() == {
        "employee_code": ["employee with this employee code already exists."]
    }
    for employee, response in zip(employees, responses, strict=True):
        employee.refresh_from_db()
        original_code, original_name = originals[employee.pk]
        assert employee.employee_code == ("RACE" if response.status_code == 200 else original_code)
        assert employee.full_name == original_name
    winner = Employee.objects.get(employee_code="RACE")
    event = AuditEvent.objects.get()
    assert (event.action, event.target_id, event.actor_id) == (
        "employee.updated",
        winner.pk,
        hr.pk,
    )


def test_disjoint_patches_preserve_both_changes_from_same_original_state(
    hr, synchronized_validation
):
    employee = Employee.objects.create(employee_code="ORIGINAL", full_name="Synthetic Original")
    responses = concurrent_requests(
        hr,
        [
            ("patch", f"/api/employees/{employee.pk}/", {"employee_code": "UPDATED"}),
            ("patch", f"/api/employees/{employee.pk}/", {"full_name": "Synthetic Updated"}),
        ],
    )

    assert synchronized_validation == [
        (employee.pk, "ORIGINAL", "Synthetic Original"),
        (employee.pk, "ORIGINAL", "Synthetic Original"),
    ]
    assert [response.status_code for response in responses] == [200, 200]
    employee.refresh_from_db()
    assert (employee.employee_code, employee.full_name) == ("UPDATED", "Synthetic Updated")
    assert AuditEvent.objects.count() == 2
    assert set(AuditEvent.objects.values_list("action", "target_id", "actor_id")) == {
        ("employee.updated", employee.pk, hr.pk)
    }


@pytest.mark.parametrize("method", ["post", "patch"])
def test_deleted_audit_actor_reraises_unrelated_integrity_error_and_rolls_back(
    hr, django_user_model, monkeypatch, method
):
    employee = Employee.objects.create(employee_code="ORIGINAL", full_name="Synthetic Original")
    validated = Barrier(2, timeout=20)
    actor_deleted = Barrier(2, timeout=20)
    original = EmployeeSerializer.is_valid

    def is_valid(serializer, *args, **kwargs):
        result = original(serializer, *args, **kwargs)
        if result:
            # Delete the actor only after authentication and real employee validation.
            validated.wait()
            actor_deleted.wait()
        return result

    def delete_actor():
        connections.close_all()
        try:
            validated.wait()
            django_user_model.objects.get(pk=hr.pk).delete()
            actor_deleted.wait()
        finally:
            connections.close_all()

    monkeypatch.setattr(EmployeeSerializer, "is_valid", is_valid)
    client = Client(raise_request_exception=False)
    client.force_login(hr)
    url = "/api/employees/" if method == "post" else f"/api/employees/{employee.pk}/"
    with ThreadPoolExecutor(max_workers=1) as pool:
        deletion = pool.submit(delete_actor)
        response = getattr(client, method)(
            url,
            {"employee_code": "UPDATED", "full_name": "Synthetic Updated"},
            content_type="application/json",
        )
        deletion.result(timeout=30)

    assert response.status_code == 500
    error = response.exc_info[1]
    assert isinstance(error, IntegrityError)
    assert error.__cause__.sqlstate == "23503"
    assert error.__cause__.diag.table_name == AuditEvent._meta.db_table
    assert not django_user_model.objects.filter(pk=hr.pk).exists()
    employee.refresh_from_db()
    assert (employee.employee_code, employee.full_name) == ("ORIGINAL", "Synthetic Original")
    assert Employee.objects.count() == 1
    assert not AuditEvent.objects.exists()
