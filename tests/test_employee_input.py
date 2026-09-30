import uuid

import pytest
from audit.models import AuditEvent
from django.contrib.auth.models import Group
from django.test import Client
from employees.models import Employee


@pytest.mark.django_db
@pytest.mark.parametrize(
    "extra",
    [
        {"salary": "1000000"},
        {"groups": ["HR"]},
        {"id": str(uuid.uuid4())},
    ],
)
def test_employee_create_rejects_unrecognized_or_read_only_fields(django_user_model, extra):
    hr = django_user_model.objects.create_user(email="hr@example.test")
    hr.groups.add(Group.objects.create(name="HR"))
    client = Client()
    client.force_login(hr)
    response = client.post(
        "/api/employees/",
        {"employee_code": "0001", "full_name": "Synthetic Employee", **extra},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert not Employee.objects.exists()
    assert not AuditEvent.objects.exists()
