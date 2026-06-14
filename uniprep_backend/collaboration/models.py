import uuid
from django.conf import settings
from django.db import models

from exit_exams.models import Course, Question, Choice


def generate_room_code():
    return uuid.uuid4().hex[:6].upper()
def generate_challenge_code():
    return generate_room_code()


class QuizChallenge(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    room_code = models.CharField(
        max_length=10,
        unique=True,
        default=generate_room_code,
        editable=False
    )

    title = models.CharField(max_length=255)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="quiz_challenges"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_quiz_challenges"
    )

    total_questions = models.PositiveIntegerField(default=5)
    duration_minutes = models.PositiveIntegerField(default=10)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.room_code})"


class ChallengeParticipant(models.Model):
    challenge = models.ForeignKey(
        QuizChallenge,
        on_delete=models.CASCADE,
        related_name="participants"
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="challenge_participations"
    )

    joined_at = models.DateTimeField(auto_now_add=True)
    is_creator = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "student"],
                name="unique_challenge_participant"
            )
        ]
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.student.username} - {self.challenge.room_code}"


class ChallengeQuestion(models.Model):
    challenge = models.ForeignKey(
        QuizChallenge,
        on_delete=models.CASCADE,
        related_name="challenge_questions"
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="challenge_questions"
    )

    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "question"],
                name="unique_challenge_question"
            ),
            models.UniqueConstraint(
                fields=["challenge", "order"],
                name="unique_challenge_question_order"
            ),
        ]

    def __str__(self):
        return f"{self.challenge.room_code} - Q{self.order}"


class ChallengeAttempt(models.Model):
    challenge = models.ForeignKey(
        QuizChallenge,
        on_delete=models.CASCADE,
        related_name="attempts"
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="challenge_attempts"
    )

    score = models.FloatField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "student"],
                name="unique_challenge_attempt"
            )
        ]

    def __str__(self):
        return f"{self.student.username} - {self.challenge.room_code}"


class ChallengeAttemptDetail(models.Model):
    attempt = models.ForeignKey(
        ChallengeAttempt,
        on_delete=models.CASCADE,
        related_name="details"
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="challenge_attempt_details"
    )

    selected_choice = models.ForeignKey(
        Choice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="challenge_attempt_details"
    )

    is_correct = models.BooleanField(default=False)
    response_time_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="unique_attempt_question"
            )
        ]

    def __str__(self):
        return f"{self.attempt} - Question {self.question.id}"