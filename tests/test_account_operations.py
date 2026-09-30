import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command


@pytest.mark.django_db
def test_technical_superuser_has_no_implicit_business_role(django_user_model):
    user = django_user_model.objects.create_superuser(
        email="operations@example.test", password="Synthetic-test-password-42"
    )
    assert user.is_staff
    assert user.is_superuser
    assert not user.groups.exists()


@pytest.mark.django_db
def test_business_role_bootstrap_is_idempotent():
    call_command("bootstrap_roles")
    call_command("bootstrap_roles")
    assert set(Group.objects.values_list("name", flat=True)) == {
        "HR",
        "KEPALA_UNIT",
        "FINANCE",
        "TECHNICAL_ADMIN",
        "INTERN",
    }
