from django.conf import settings
from django.db import models
from exit_exams.models import Course, Domain, Topic


class StudyMaterial(models.Model):
    class FileType(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"
        URL = "url", "URL"

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_materials"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_materials"
    )

    domain = models.ForeignKey(
        Domain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_materials"
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_materials"
    )

    title = models.CharField(max_length=255)

    file = models.FileField(
        upload_to="study_materials/",
        null=True,
        blank=True
    )

    source_url = models.URLField(blank=True)

    file_type = models.CharField(
        max_length=10,
        choices=FileType.choices
    )

    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING
    )

    error_message = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["course"]),
            models.Index(fields=["domain"]),
            models.Index(fields=["topic"]),
            models.Index(fields=["processing_status"]),
        ]

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="chunks"
    )

    qdrant_point_id = models.CharField(
        max_length=255,
        unique=True
    )

    chunk_text = models.TextField()
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("material", "chunk_index")
        ordering = ["material", "chunk_index"]
        indexes = [
            models.Index(fields=["material"]),
            models.Index(fields=["qdrant_point_id"]),
        ]

    def __str__(self):
        return f"{self.material.title} - Chunk {self.chunk_index}"


class AIChatSession(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_chat_sessions"
    )

    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="chat_sessions"
    )

    title = models.CharField(max_length=255, default="AI Study Chat")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.username} - {self.material.title}"


class AIChatMessage(models.Model):
    class Sender(models.TextChoices):
        USER = "user", "User"
        AI = "ai", "AI"

    session = models.ForeignKey(
        AIChatSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sender = models.CharField(
        max_length=10,
        choices=Sender.choices
    )

    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender}: {self.message[:50]}"


class MaterialSummary(models.Model):
    material = models.OneToOneField(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="summary"
    )

    summary_text = models.TextField()
    key_points = models.JSONField(default=list, blank=True)
    important_terms = models.JSONField(default=list, blank=True)

    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Summary - {self.material.title}"


class GeneratedFlashcard(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_flashcards"
    )

    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="flashcards"
    )

    front = models.TextField()
    back = models.TextField()

    difficulty = models.CharField(max_length=20, default="medium")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.front[:60]


class GeneratedQuiz(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_quizzes"
    )

    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="generated_quizzes"
    )

    title = models.CharField(max_length=255, default="AI Generated Quiz")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class GeneratedQuizQuestion(models.Model):
    quiz = models.ForeignKey(
        GeneratedQuiz,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    question_text = models.TextField()

    choices = models.JSONField(
        default=list,
        help_text="Example: ['A', 'B', 'C', 'D']"
    )

    correct_answer = models.CharField(max_length=255)
    explanation = models.TextField(blank=True)

    def __str__(self):
        return self.question_text[:60]
