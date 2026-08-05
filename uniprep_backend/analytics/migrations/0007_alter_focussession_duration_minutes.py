from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0006_alter_notification_notification_type_learningpath_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="focussession",
            name="duration_minutes",
            field=models.FloatField(default=0),
        ),
    ]