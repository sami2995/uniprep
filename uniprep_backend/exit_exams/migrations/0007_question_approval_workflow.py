from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_question_statuses(apps, schema_editor):
    Question = apps.get_model("exit_exams", "Question")

    Question.objects.filter(is_active=True).update(status="approved")
    Question.objects.filter(is_active=False).update(status="archived")


def reset_question_statuses(apps, schema_editor):
    Question = apps.get_model("exit_exams", "Question")
    Question.objects.update(status="draft")


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("exit_exams", "0006_department_teacher_assignments"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_questions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("submitted", "Submitted"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("archived", "Archived"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="question",
            name="rejection_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="question",
            name="submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            backfill_question_statuses,
            reset_question_statuses,
        ),
        migrations.AddIndex(
            model_name="question",
            index=models.Index(fields=["status"], name="exit_exams__status_4e2931_idx"),
        ),
        migrations.AddIndex(
            model_name="question",
            index=models.Index(fields=["created_by"], name="exit_exams__created_3433a1_idx"),
        ),
    ]
