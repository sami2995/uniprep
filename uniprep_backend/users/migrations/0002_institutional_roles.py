from django.db import migrations, models


def migrate_admins_to_department_heads(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    CustomUser.objects.filter(role="admin").update(role="department_head")


def migrate_department_heads_to_admins(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    CustomUser.objects.filter(role="department_head").update(role="admin")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="role",
            field=models.CharField(
                choices=[
                    ("student", "Student"),
                    ("teacher", "Teacher"),
                    ("department_head", "Department Head"),
                    ("system_admin", "System Admin"),
                ],
                default="student",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            migrate_admins_to_department_heads,
            migrate_department_heads_to_admins,
        ),
    ]
