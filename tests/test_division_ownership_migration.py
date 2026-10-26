import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)


def test_legacy_owner_can_be_assigned_explicitly_between_schema_and_required_migrations():
    latest, Branch, Division, _ = old_models()
    try:
        owner = Branch.objects.create(name="Existing Owner")
        Branch.objects.create(name="Another Branch")
        division = Division.objects.create(name="Existing Division")
        intermediate = [("organization", "0004_division_branch")]
        MigrationExecutor(connection).migrate(intermediate)
        apps = MigrationExecutor(connection).loader.project_state(intermediate).apps
        transitional = apps.get_model("organization", "Division")
        assert transitional.objects.get(pk=division.pk).branch_id is None
        assert transitional.objects.filter(pk=division.pk).update(branch_id=owner.pk) == 1
        MigrationExecutor(connection).migrate(latest)
        apps = MigrationExecutor(connection).loader.project_state(latest).apps
        assert (
            apps.get_model("organization", "Division").objects.get(pk=division.pk).branch_id
            == owner.pk
        )
    finally:
        Division.objects.all().delete()
        MigrationExecutor(connection).migrate(latest)


OLD = [
    ("organization", "0003_employee_group_references"),
    ("employees", "0007_employee_primary_groups"),
]


def old_models():
    assert connection.settings_dict["NAME"].startswith("test_")
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    executor.migrate(OLD)
    apps = executor.loader.project_state(OLD).apps
    return (
        latest,
        apps.get_model("organization", "Branch"),
        apps.get_model("organization", "Division"),
        apps.get_model("employees", "Employee"),
    )


def test_single_existing_branch_owns_legacy_division_without_changing_employee_identity():
    latest, Branch, Division, Employee = old_models()
    try:
        branch = Branch.objects.create(name="Existing Branch")
        division = Division.objects.create(name="Existing Division")
        employee = Employee.objects.create(employee_code="0009", full_name="Synthetic Existing")
        MigrationExecutor(connection).migrate(latest)
        apps = MigrationExecutor(connection).loader.project_state(latest).apps
        restored = apps.get_model("organization", "Division").objects.get(pk=division.pk)
        assert restored.branch_id == branch.pk
        assert restored.name == division.name
        assert apps.get_model("organization", "Branch").objects.count() == 1
        assert apps.get_model("organization", "Division").objects.count() == 1
        preserved = apps.get_model("employees", "Employee").objects.get(pk=employee.pk)
        assert (
            preserved.employee_code,
            preserved.full_name,
            preserved.branch_id,
            preserved.division_id,
        ) == ("0009", "Synthetic Existing", None, None)
    finally:
        MigrationExecutor(connection).migrate(latest)


@pytest.mark.parametrize("branch_count", [0, 2])
def test_ambiguous_legacy_division_ownership_blocks_migration_without_losing_data(branch_count):
    latest, Branch, Division, _ = old_models()
    try:
        for index in range(branch_count):
            Branch.objects.create(name=f"Synthetic Branch {index}")
        division = Division.objects.create(name="Existing Division")
        with pytest.raises(RuntimeError, match="explicit branch mapping"):
            MigrationExecutor(connection).migrate(latest)
        assert Division.objects.get(pk=division.pk).name == "Existing Division"
        assert Branch.objects.count() == branch_count
    finally:
        Division.objects.all().delete()
        MigrationExecutor(connection).migrate(latest)
