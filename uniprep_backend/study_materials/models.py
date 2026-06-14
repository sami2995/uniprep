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
    file = models.FileField(upload_to="study_materials/", null=True, blank=True)
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

    def __str__(self):
        return self.title
class DocumentChunk(models.Model):
    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="chunks"
    )

    qdrant_point_id = models.CharField(max_length=255, unique=True)

    chunk_text = models.TextField()
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("material", "chunk_index")
        indexes = [
            models.Index(fields=["material"]),
            models.Index(fields=["qdrant_point_id"]),
        ]

    def __str__(self):
        return f"{self.material.title} - Chunk {self.chunk_index}"
