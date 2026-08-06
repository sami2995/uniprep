from django.db import migrations, models
import django.db.models.deletion


def mark_existing_accounts_verified(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    CustomUser.objects.all().update(verification="verified")


def reset_verification_on_reverse(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    CustomUser.objects.all().update(verification="pending")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_customuser_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="verification",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("verified", "Verified"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="verified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="verified_students",
                to="users.customuser",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="rejection_reason",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(mark_existing_accounts_verified, reset_verification_on_reverse),
    ]
