from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_course_assignments_to_topics(apps, schema_editor):
    """For every existing TeacherCourseAssignment, create TeacherTopicAssignment
    records for each Topic that belongs to that Course.

    This preserves existing teacher permissions: a teacher previously assigned
    to a Course becomes assigned to every Topic in that Course.
    """
    TeacherCourseAssignment = apps.get_model("exit_exams", "TeacherCourseAssignment")
    TeacherTopicAssignment = apps.get_model("exit_exams", "TeacherTopicAssignment")
    Topic = apps.get_model("exit_exams", "Topic")

    for assignment in TeacherCourseAssignment.objects.all().iterator():
        topics = Topic.objects.filter(domain__course_id=assignment.course_id)
        for topic in topics.iterator():
            TeacherTopicAssignment.objects.get_or_create(
                teacher_id=assignment.teacher_id,
                topic_id=topic.id,
                defaults={
                    "assigned_by_id": None,
                    "active": True,
                },
            )


def reverse_topic_to_course_assignments(apps, schema_editor):
    """Reverse is a no-op: dropping TeacherTopicAssignment rows is not a safe
    way to reconstruct the original course-level assignment granularity, so we
    simply delete the topic-level rows that this migration created."""
    TeacherTopicAssignment = apps.get_model("exit_exams", "TeacherTopicAssignment")
    TeacherTopicAssignment.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("exit_exams", "0012_systemsettings_mastery_minimum_attempts_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TeacherTopicAssignment",
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
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("active", models.BooleanField(default=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="topic_assignments_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "teacher",
                    models.ForeignKey(
                        limit_choices_to={"role": "teacher"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="topic_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "topic",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="teacher_assignments",
                        to="exit_exams.topic",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "topic__domain__course__name",
                    "topic__domain__name",
                    "topic__name",
                    "teacher__username",
                ],
                "unique_together": {("teacher", "topic")},
                "indexes": [
                    models.Index(fields=["teacher"], name="exit_exams__teacher_e02b6b_idx"),
                    models.Index(fields=["topic"], name="exit_exams__topic_i_e91c44_idx"),
                    models.Index(fields=["active"], name="exit_exams__active_00d9d9_idx"),
                ],
            },
        ),
        migrations.RunPython(
            migrate_course_assignments_to_topics,
            reverse_code=reverse_topic_to_course_assignments,
        ),
    ]