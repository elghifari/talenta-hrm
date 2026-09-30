import pytest
from django.test import Client


@pytest.mark.django_db
@pytest.mark.parametrize("email", [None, "", "   "])
def test_account_creation_requires_a_nonempty_email(django_user_model, email):
    with pytest.raises(ValueError, match="Email is required"):
        django_user_model.objects.create_user(email=email)


@pytest.mark.django_db
@pytest.mark.parametrize("flags", [{"is_staff": False}, {"is_superuser": False}])
def test_superuser_creation_rejects_disabled_privilege_flags(django_user_model, flags):
    with pytest.raises(ValueError):
        django_user_model.objects.create_superuser(email="ops@example.test", **flags)


@pytest.mark.django_db
def test_superuser_without_hr_role_cannot_read_business_data(django_user_model):
    user = django_user_model.objects.create_superuser(email="ops@example.test")
    client = Client()
    client.force_login(user)
    assert client.get("/api/employees/").status_code == 403
