import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0003_employee_group_references"),
        ("employees", "0007_employee_primary_groups"),
    ]

    operations = [
        migrations.AddField(
            model_name="division",
            name="branch",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="divisions",
                to="organization.branch",
            ),
        ),
    ]
