from django.db import migrations, models


def set_magang_type(apps, schema_editor):
    employee = apps.get_model("employees", "Employee")
    employee.objects.using(schema_editor.connection.alias).filter(
        employment_status="magang"
    ).update(pkwt_type="yayasan")


def clear_magang_type(apps, schema_editor):
    employee = apps.get_model("employees", "Employee")
    employee.objects.using(schema_editor.connection.alias).filter(
        employment_status="magang"
    ).update(pkwt_type="")


class Migration(migrations.Migration):
    dependencies = [("employees", "0008_employment_classification")]

    operations = [
        migrations.RemoveConstraint(model_name="employee", name="valid_employee_employment_pair"),
        migrations.RunPython(set_magang_type, clear_magang_type),
        migrations.AddConstraint(
            model_name="employee",
            constraint=models.CheckConstraint(
                condition=(models.Q(employment_status="kontrak") & ~models.Q(pkwt_type=""))
                | models.Q(employment_status="magang", pkwt_type="yayasan")
                | (~models.Q(employment_status__in=["kontrak", "magang"]) & models.Q(pkwt_type="")),
                name="valid_employee_employment_pair",
            ),
        ),
    ]
