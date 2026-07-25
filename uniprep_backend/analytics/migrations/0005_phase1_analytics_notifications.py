# Generated for UniPrep Phase 1 analytics and notifications.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_wrong_attempts(apps, schema_editor):
    StudentTopicPerformance = apps.get_model("analytics", "StudentTopicPerformance")

    for performance in StudentTopicPerformance.objects.all():
        performance.wrong_attempts = max(
            0,
            performance.total_attempts - performance.correct_attempts,
        )
        performance.save(update_fields=["wrong_attempts"])


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0004_focussession"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="studenttopicperformance",
            name="average_time_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="studenttopicperformance",
            name="trend",
            field=models.CharField(
                choices=[
                    ("improving", "Improving"),
                    ("declining", "Declining"),
                    ("stable", "Stable"),
                ],
                default="stable",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="studenttopicperformance",
            name="wrong_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(backfill_wrong_attempts, migrations.RunPython.noop),
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=150)),
                ("message", models.TextField()),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("mock_available", "Mock Available"),
                            ("weak_topic", "Weak Topic"),
                            ("battle_invite", "Battle Invite"),
                            ("material_uploaded", "Material Uploaded"),
                            ("weekly_reminder", "Weekly Reminder"),
                        ],
                        max_length=30,
                    ),
                ),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["student", "is_read"],
                name="analytics_n_student_b53bb2_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["created_at"],
                name="analytics_n_created_200ed4_idx",
            ),
        ),
    ]
