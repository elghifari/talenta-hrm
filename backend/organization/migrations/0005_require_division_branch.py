import django.db.models.deletion
from django.db import migrations, models
from django.db.models.functions import Lower


def assign_existing_divisions(apps, schema_editor):
    alias = schema_editor.connection.alias
    division = apps.get_model("organization", "Division")
    unowned = division.objects.using(alias).filter(branch__isnull=True)
    if unowned.exists():
        branch_ids = list(
            apps.get_model("organization", "Branch")
            .objects.using(alias)
            .values_list("pk", flat=True)
        )
        if len(branch_ids) != 1:
            raise RuntimeError(
                "Existing divisions need an explicit branch mapping before migration."
            )
        unowned.update(branch_id=branch_ids[0])
    employee = apps.get_model("employees", "Employee")
    if (
        employee.objects.using(alias)
        .filter(division__isnull=False)
        .filter(
            models.Q(branch__isnull=True) | ~models.Q(branch_id=models.F("division__branch_id"))
        )
        .exists()
    ):
        raise RuntimeError(
            "Existing employee groups need an explicit branch mapping before migration."
        )


class Migration(migrations.Migration):
    dependencies = [("organization", "0004_division_branch")]

    operations = [
        migrations.RunPython(assign_existing_divisions, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="division",
            name="branch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="divisions",
                to="organization.branch",
            ),
        ),
        migrations.RemoveConstraint(model_name="division", name="unique_division_name_ci"),
        migrations.AddConstraint(
            model_name="division",
            constraint=models.UniqueConstraint(
                Lower("name"), models.F("branch"), name="unique_division_name_per_branch_ci"
            ),
        ),
        migrations.AlterModelOptions(
            name="division", options={"ordering": ["branch__name", "name", "id"]}
        ),
    ]
