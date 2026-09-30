import pytest
from django.apps import apps
from django.contrib.auth.models import Group
from django.test import Client


@pytest.mark.django_db
def test_employee_creation_records_actor_without_copying_personal_data(django_user_model):
    assert apps.is_installed("audit"), "Employee write audit is missing"
    AuditEvent = apps.get_model("audit", "AuditEvent")
    hr = django_user_model.objects.create_user(email="hr@example.test")
    hr.groups.add(Group.objects.create(name="HR"))
    client = Client()
    client.force_login(hr)
    response = client.post(
        "/api/employees/",
        {"employee_code": "0007", "full_name": "Synthetic Employee"},
        content_type="application/json",
    )
    assert response.status_code == 201
    event = AuditEvent.objects.get()
    assert event.actor == hr
    assert event.action == "employee.created"
    assert str(event.target_id) == response.json()["id"]
    assert not hasattr(event, "full_name")
