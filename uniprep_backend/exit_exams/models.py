from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Course(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses"
    )

    def __str__(self):
        return self.name


class TeacherCourseAssignment(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_assignments",
        limit_choices_to={"role": "teacher"}
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="teacher_assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("teacher", "course")
        ordering = ["course__name", "teacher__username"]

    def clean(self):
        if self.teacher and getattr(self.teacher, "role", None) != "teacher":
            raise ValidationError("Only TEACHER users can be assigned to courses.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.teacher.username} - {self.course.name}"


class Domain(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="domains"
    )
    name = models.CharField(max_length=100)
    importance_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.15
    )

    class Meta:
        unique_together = ("course", "name")
        ordering = ["course__name", "name"]

    def __str__(self):
        return f"{self.course.name} - {self.name}"


class Topic(models.Model):
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="topics"
    )
    name = models.CharField(max_length=100)
    importance_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.10
    )

    class Meta:
        unique_together = ("domain", "name")
        ordering = ["domain__name", "name"]

    def __str__(self):
        return f"{self.domain.name} - {self.name}"


class Question(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    class SourceType(models.TextChoices):
        MANUAL = "manual", "Manual"
        IMPORTED = "imported", "Imported"

    class BloomLevel(models.TextChoices):
        KNOWLEDGE = "knowledge", "Knowledge"
        COMPREHENSION = "comprehension", "Comprehension"
        APPLICATION = "application", "Application"
        ANALYSIS = "analysis", "Analysis"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    text = models.TextField()
    bloom_level = models.CharField(
        max_length=20,
        choices=BloomLevel.choices,
        default=BloomLevel.KNOWLEDGE
    )
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM
    )
    explanation = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_questions"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_questions"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_questions"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_questions"
    )
    originating_pdf_import = models.ForeignKey(
        "ExamPdfImport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_questions"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.MANUAL
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["topic"]),
            models.Index(fields=["difficulty"]),
            models.Index(fields=["bloom_level"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self):
        return self.text[:80]


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices"
    )
    text = models.TextField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:80]
class MockExam(models.Model):
    class Status(models.TextChoices):
        GENERATED = "generated", "Generated"
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        EXPIRED = "expired", "Expired"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mock_exams"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="mock_exams"
    )
    title = models.CharField(max_length=150, default="Mock Exam")
    exam_number = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField(default=50)
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.GENERATED
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course", "exam_number")
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.student.username} - {self.course.name} - Exam {self.exam_number}"


class MockExamQuestion(models.Model):
    mock_exam = models.ForeignKey(
        MockExam,
        on_delete=models.CASCADE,
        related_name="mock_questions"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="mock_exam_links"
    )
    order = models.PositiveIntegerField()

    class Meta:
        unique_together = [
            ("mock_exam", "question"),
            ("mock_exam", "order"),
        ]
        ordering = ["order"]

    def __str__(self):
        return f"{self.mock_exam} - Q{self.order}"
class ExamAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        AUTO_SUBMITTED = "auto_submitted", "Auto Submitted"

    mock_exam = models.OneToOneField(
        MockExam,
        on_delete=models.CASCADE,
        related_name="attempt"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_attempts"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS
    )
    total_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.student.username} - {self.mock_exam.title}"


class AttemptDetail(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name="details"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="attempt_details"
    )
    selected_choice = models.ForeignKey(
        Choice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selected_attempts"
    )
    is_correct = models.BooleanField(default=False)
    response_time_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("attempt", "question")
        indexes = [
            models.Index(fields=["question"]),
            models.Index(fields=["is_correct"]),
        ]

    def clean(self):
        if self.selected_choice and self.selected_choice.question_id != self.question_id:
            raise ValidationError("Selected choice does not belong to this question.")

    def __str__(self):
        return f"{self.attempt} - {self.question.text[:40]}"
class ExamPdfImport(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        NEEDS_REVIEW = "needs_review", "Needs Review"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        FAILED = "failed", "Failed"

    class SourceType(models.TextChoices):
        PAST_EXAM = "past_exam", "Past Exam"
        MOCK_EXAM = "mock_exam", "Mock Exam"
        PRACTICE = "practice", "Practice"
        OTHER = "other", "Other"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="exam_pdf_imports"
    )

    title = models.CharField(max_length=255)

    file = models.FileField(
        upload_to="exam_imports/"
    )

    source_type = models.CharField(
        max_length=30,
        choices=SourceType.choices,
        default=SourceType.MOCK_EXAM
    )

    year = models.PositiveIntegerField(null=True, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_exam_pdfs"
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_exam_pdfs"
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.UPLOADED
    )

    extracted_text = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class ExtractedQuestion(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    exam_import = models.ForeignKey(
        ExamPdfImport,
        on_delete=models.CASCADE,
        related_name="extracted_questions"
    )

    question_number = models.PositiveIntegerField(null=True, blank=True)

    question_text = models.TextField()

    option_a = models.TextField(blank=True)
    option_b = models.TextField(blank=True)
    option_c = models.TextField(blank=True)
    option_d = models.TextField(blank=True)

    correct_answer = models.CharField(
        max_length=1,
        blank=True,
        help_text="A, B, C, or D"
    )

    explanation = models.TextField(blank=True)

    domain = models.ForeignKey(
        Domain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extracted_questions"
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extracted_questions"
    )

    difficulty = models.CharField(
        max_length=10,
        choices=Question.Difficulty.choices,
        default=Question.Difficulty.MEDIUM
    )

    bloom_level = models.CharField(
        max_length=20,
        choices=Question.BloomLevel.choices,
        default=Question.BloomLevel.KNOWLEDGE
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    approved_question = models.OneToOneField(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_extracted_question"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text[:80]
class ExamBlueprint(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="exam_blueprints"
    )

    title = models.CharField(max_length=150)

    total_questions = models.PositiveIntegerField(default=100)

    duration_minutes = models.PositiveIntegerField(default=180)

    pass_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00
    )

    marks_per_question = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00
    )

    bloom_distribution = models.JSONField(default=dict, blank=True)

    difficulty_distribution = models.JSONField(
        default=dict,
        blank=True,
        help_text='e.g. {"easy": 30, "medium": 50, "hard": 20}'
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_blueprints"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "title")
        ordering = ["course__name", "title"]

    def __str__(self):
        return f"{self.course.name} - {self.title}"


class ExamBlueprintDomainRule(models.Model):
    blueprint = models.ForeignKey(
        ExamBlueprint,
        on_delete=models.CASCADE,
        related_name="domain_rules"
    )

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name="blueprint_rules"
    )

    number_of_questions = models.PositiveIntegerField()

    class Meta:
        unique_together = ("blueprint", "domain")

    def __str__(self):
        return f"{self.blueprint.title} - {self.domain.name}: {self.number_of_questions}"
class ExamBlueprintTopicRule(models.Model):
    blueprint = models.ForeignKey(
        ExamBlueprint,
        on_delete=models.CASCADE,
        related_name="topic_rules"
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="blueprint_rules"
    )

    question_count = models.PositiveIntegerField()

    class Meta:
        unique_together = ("blueprint", "topic")

    def __str__(self):
        return (
            f"{self.blueprint} - "
            f"{self.topic.name}: {self.question_count}"
        )


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        BLUEPRINT_CHANGED = "blueprint_changed", "Blueprint Changed"
        ASSIGNMENT_CHANGED = "assignment_changed", "Assignment Changed"
        SYSTEM_SETTINGS_UPDATED = "system_settings_updated", "System Settings Updated"
        USER_DEACTIVATED = "user_deactivated", "User Deactivated"
        USER_REACTIVATED = "user_reactivated", "User Reactivated"
        PASSWORD_RESET_BY_ADMIN = "password_reset_by_admin", "Password Reset By Admin"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs"
    )
    action = models.CharField(
        max_length=30,
        choices=Action.choices
    )
    entity_type = models.CharField(
        max_length=50,
        help_text="e.g. question, blueprint, assignment"
    )
    entity_id = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    previous_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["user"]),
            models.Index(fields=["action"]),
            models.Index(fields=["-timestamp"]),
        ]

    def __str__(self):
        return (
            f"{self.user} - {self.action} - "
            f"{self.entity_type}#{self.entity_id}"
        )


class SystemSettings(models.Model):
    """Singleton — only one row should ever exist."""
    default_passing_score = models.PositiveIntegerField(default=50)
    default_exam_duration_minutes = models.PositiveIntegerField(default=60)
    max_battle_participants = models.PositiveIntegerField(default=8)
    mastery_threshold_accuracy = models.PositiveIntegerField(default=80)
    mastery_minimum_attempts = models.PositiveIntegerField(default=3)
    quiz_unlock_score = models.PositiveIntegerField(default=70)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "System Settings"

