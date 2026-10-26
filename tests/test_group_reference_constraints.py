from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from audit.models import AuditEvent
from django.db import IntegrityError, connections, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client
from employees.models import Employee
from organization.models import Branch, Division
from organization.serializers import ReferenceSerializer
from test_employee_grouping import hr as hr


@pytest.mark.django_db
@pytest.mark.parametrize("model,field", [(Branch, "branch"), (Division, "division")])
def test_reference_database_uniqueness_and_referenced_delete_protection(model, field):
    owner = {"branch": Branch.objects.create(name="Owner")} if model is Division else {}
    record = model.objects.create(name="Synthetic Choice", **owner)
    Employee.objects.create(employee_code="0009", full_name="Synthetic Grouped", **{field: record})
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(name="synthetic choice", **owner)
    with pytest.raises(ProtectedError):
        record.delete()
    assert model.objects.count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind,model", [("branches", Branch), ("divisions", Division)])
def test_concurrent_case_insensitive_choice_creation_has_one_audited_winner(
    hr, monkeypatch, kind, model
):
    client, _ = hr
    owner = {"branch": str(Branch.objects.create(name="Owner").pk)} if model is Division else {}
    barrier = Barrier(2)
    original = ReferenceSerializer.is_valid

    def together(serializer, *args, **kwargs):
        result = original(serializer, *args, **kwargs)
        barrier.wait(timeout=20)
        return result

    monkeypatch.setattr(ReferenceSerializer, "is_valid", together)

    def create(name):
        connections.close_all()
        try:
            worker = Client()
            worker.cookies = client.cookies.copy()
            return worker.post(
                f"/api/organization/{kind}/",
                {"name": name, **owner},
                content_type="application/json",
            ).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create, name) for name in ("Concurrent Choice", "concurrent choice")]
        statuses = [future.result(timeout=40) for future in futures]
    assert sorted(statuses) == [201, 400]
    assert model.objects.count() == 1
    assert AuditEvent.objects.count() == 1
