import pytest
from django.contrib.auth.models import Group
from django.test import Client


@pytest.mark.django_db
def test_hr_creates_employee_with_stable_text_identifier(django_user_model):
    hr = django_user_model.objects.create_user(email="hr@example.test")
    hr.groups.add(Group.objects.create(name="HR"))
    client = Client()
    client.force_login(hr)
    response = client.post(
        "/api/employees/",
        {"employee_code": "0007", "full_name": "Synthetic Employee"},
        content_type="application/json",
    )
    assert response.status_code == 201, response.content
    employee_id = response.json()["id"]
    response = client.get(f"/api/employees/{employee_id}/")
    assert response.status_code == 200
    assert response.json()["employee_code"] == "0007"
    assert response.json()["full_name"] == "Synthetic Employee"
