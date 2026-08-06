from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exit_exams", "0013_teachertopicassignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemsettings",
            name="restrict_blueprint_to_official_questions",
            field=models.BooleanField(default=True),
        ),
    ]
