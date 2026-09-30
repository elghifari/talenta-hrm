import pytest


def test_personal_email_is_the_login_identifier(django_user_model):
    assert django_user_model.USERNAME_FIELD == "email"


@pytest.mark.django_db
def test_create_user_with_email_and_password(django_user_model):
    user = django_user_model.objects.create_user(
        email="hr@example.test", password="Synthetic-test-password-42"
    )
    assert user.check_password("Synthetic-test-password-42")
    assert user.email == "hr@example.test"
