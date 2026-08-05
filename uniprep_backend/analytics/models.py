from django.conf import settings
from django.db import models
from exit_exams.models import Question, Topic, Domain, Course


class StudentTopicPerformance(models.Model):
    class Trend(models.TextChoices):
        IMPROVING = "improving", "Improving"
        DECLINING = "declining", "Declining"
        STABLE = "stable", "Stable"

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
    wrong_attempts = models.PositiveIntegerField(default=0)
    total_attempts = models.PositiveIntegerField(default=0)
    average_time_seconds = models.PositiveIntegerField(default=0)
    trend = models.CharField(
        max_length=20,
        choices=Trend.choices,
        default=Trend.STABLE
    )
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


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        MOCK_AVAILABLE = "mock_available", "Mock Available"
        WEAK_TOPIC = "weak_topic", "Weak Topic"
        BATTLE_INVITE = "battle_invite", "Battle Invite"
        MATERIAL_UPLOADED = "material_uploaded", "Material Uploaded"
        WEEKLY_REMINDER = "weekly_reminder", "Weekly Reminder"
        LEARNING_PATH_READY = "learning_path_ready", "Learning Path Ready"
        LEARNING_STEP_UNLOCKED = "learning_step_unlocked", "Learning Step Unlocked"
        LEARNING_PATH_COMPLETED = "learning_path_completed", "Learning Path Completed"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices
    )
    target_url = models.CharField(max_length=255, blank=True, default="")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student", "is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.title}"


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
    duration_minutes = models.FloatField(default=0)

    def __str__(self):
        return f"{self.student.username} - {self.duration_minutes:.2f} minutes"


class LearningPath(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="learning_paths"
    )
    topic = models.CharField(max_length=150)
    subtopic = models.CharField(max_length=150, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_progress')
    current_step = models.CharField(max_length=15, default='summary')  # summary|flashcards|quiz|mini_mock|scheduled
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student", "status"]),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.topic} ({self.status})"


class LearningStep(models.Model):
    STEP_TYPES = [
        ('summary', 'Summary'),
        ('flashcards', 'Flashcards'),
        ('quiz', 'Quiz'),
        ('mini_mock', 'Mini Mock'),
    ]

    learning_path = models.ForeignKey(
        LearningPath,
        related_name='steps',
        on_delete=models.CASCADE
    )
    step_type = models.CharField(max_length=15, choices=STEP_TYPES)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.learning_path.topic} - {self.step_type} ({'Done' if self.completed else 'Pending'})"
