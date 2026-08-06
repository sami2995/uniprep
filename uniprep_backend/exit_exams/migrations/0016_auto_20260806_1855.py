from django.db import migrations


def create_departments(apps, schema_editor):
    Department = apps.get_model("exit_exams", "Department")

    departments = [
        {
            "name": "Computer Science",
            "code": "CS",
        },
        {
            "name": "Software Engineering",
            "code": "SE",
        },
        {
            "name": "Information Technology",
            "code": "IT",
        },
    ]

    for department in departments:
        Department.objects.get_or_create(
            code=department["code"],
            defaults={
                "name": department["name"],
            }
        )


class Migration(migrations.Migration):

    dependencies = [
        ("exit_exams", "0015_consolidate_courses"),
    ]

    operations = [
        migrations.RunPython(create_departments),
    ]