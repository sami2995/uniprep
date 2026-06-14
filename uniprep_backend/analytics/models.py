from django.conf import settings
from django.db import models
from exit_exams.models import Question, Topic, Domain, Course


class StudentTopicPerformance(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_performances"
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="student_topic_performances"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="student_topic_performances"
    )

    correct_attempts = models.PositiveIntegerField(default=0)
    total_attempts = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "topic")
        indexes = [
            models.Index(fields=["student", "topic"]),
            models.Index(fields=["domain"]),
        ]

    @property
    def accuracy(self):
        if self.total_attempts == 0:
            return 0
        return round((self.correct_attempts / self.total_attempts) * 100, 1)

    def __str__(self):
        return f"{self.student.username} - {self.topic.name}: {self.accuracy}%"
class SpacedRepetitionQueue(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="spaced_repetition_items"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="spaced_repetition_items"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="spaced_repetition_items"
    )

    next_review_date = models.DateField()
    interval_days = models.PositiveIntegerField(default=1)
    mastery_level = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "question")
        indexes = [
            models.Index(fields=["student", "next_review_date"]),
            models.Index(fields=["topic"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.topic.name}"
class ReadinessScore(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="readiness_scores"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="readiness_scores"
    )
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "course")
        indexes = [
            models.Index(fields=["student", "course"]),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.course.name}: {self.score}%"
class FocusSession(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="focus_sessions"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="focus_sessions"
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="focus_sessions"
    )

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.student.username} - {self.duration_minutes} minutes"