from django.contrib import admin
from .models import (
    Department, Course, TeacherCourseAssignment, TeacherTopicAssignment,
    Domain, Topic,
    Question, Choice, MockExam, MockExamQuestion, ExamAttempt,
    AttemptDetail, ExamPdfImport, ExtractedQuestion, ExamBlueprint,
    ExamBlueprintDomainRule, AuditLog, SystemSettings,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "course_count", "created_at"]
    search_fields = ["name", "code"]
    ordering = ["name"]

    def course_count(self, obj):
        return obj.courses.count()
    course_count.admin_order_field = "courses__count"


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["name", "department_code", "department_name"]
    list_filter = ["department"]
    search_fields = ["name", "department__name", "department__code"]

    def department_code(self, obj):
        return obj.department.code if obj.department else "-"

    def department_name(self, obj):
        return obj.department.name if obj.department else "-"


@admin.register(TeacherCourseAssignment)
class TeacherCourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ["teacher_username", "course_name", "department_name", "assigned_at"]
    list_filter = ["course__department"]
    search_fields = ["teacher__username", "course__name"]

    def teacher_username(self, obj):
        return obj.teacher.username

    def course_name(self, obj):
        return obj.course.name

    def department_name(self, obj):
        return obj.course.department.name if obj.course.department else "-"


@admin.register(TeacherTopicAssignment)
class TeacherTopicAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "teacher_username", "topic_name", "domain_name",
        "course_name", "active", "assigned_at",
    ]
    list_filter = ["active", "topic__domain__course__department", "topic__domain__course"]
    search_fields = ["teacher__username", "topic__name", "topic__domain__name"]

    def teacher_username(self, obj):
        return obj.teacher.username

    def topic_name(self, obj):
        return obj.topic.name

    def domain_name(self, obj):
        return obj.topic.domain.name

    def course_name(self, obj):
        return obj.topic.domain.course.name


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ["name", "course_name", "importance_weight"]
    list_filter = ["course"]
    search_fields = ["name", "course__name"]

    def course_name(self, obj):
        return obj.course.name


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name", "domain_name", "importance_weight"]
    list_filter = ["domain__course"]
    search_fields = ["name", "domain__name"]

    def domain_name(self, obj):
        return obj.domain.name


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        "id", "text_preview", "topic_name", "difficulty",
        "status", "created_by_username", "created_at",
    ]
    list_filter = [
        "status", "difficulty", "bloom_level", "source_type",
        "topic__domain__course__department",
    ]
    search_fields = ["text", "topic__name", "topic__domain__name"]

    def text_preview(self, obj):
        return obj.text[:80]

    def topic_name(self, obj):
        return obj.topic.name

    def created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else "-"


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ["text_preview", "is_correct", "question_id"]
    list_filter = ["is_correct"]
    search_fields = ["text"]

    def text_preview(self, obj):
        return obj.text[:80]


@admin.register(MockExam)
class MockExamAdmin(admin.ModelAdmin):
    list_display = ["title", "student_username", "course_name", "status", "generated_at"]
    list_filter = ["status", "course"]
    search_fields = ["student__username", "course__name"]

    def student_username(self, obj):
        return obj.student.username

    def course_name(self, obj):
        return obj.course.name


@admin.register(MockExamQuestion)
class MockExamQuestionAdmin(admin.ModelAdmin):
    list_display = ["mock_exam", "question_preview", "order"]

    def question_preview(self, obj):
        return obj.question.text[:60]


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ["student_username", "exam_title", "total_score", "status", "submitted_at"]
    list_filter = ["status"]

    def student_username(self, obj):
        return obj.student.username

    def exam_title(self, obj):
        return obj.mock_exam.title


@admin.register(AttemptDetail)
class AttemptDetailAdmin(admin.ModelAdmin):
    list_display = ["attempt", "question_preview", "is_correct"]
    list_filter = ["is_correct"]

    def question_preview(self, obj):
        return obj.question.text[:60]


@admin.register(ExamPdfImport)
class ExamPdfImportAdmin(admin.ModelAdmin):
    list_display = ["title", "course_name", "source_type", "status", "uploaded_by_username", "uploaded_at"]
    list_filter = ["status", "source_type"]
    search_fields = ["title", "course__name"]

    def course_name(self, obj):
        return obj.course.name

    def uploaded_by_username(self, obj):
        return obj.uploaded_by.username if obj.uploaded_by else "-"


@admin.register(ExtractedQuestion)
class ExtractedQuestionAdmin(admin.ModelAdmin):
    list_display = ["id", "text_preview", "exam_import", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["question_text"]

    def text_preview(self, obj):
        return obj.question_text[:80]


@admin.register(ExamBlueprint)
class ExamBlueprintAdmin(admin.ModelAdmin):
    list_display = ["title", "course_name", "total_questions", "is_active", "created_at"]
    list_filter = ["is_active", "course"]
    search_fields = ["title", "course__name"]

    def course_name(self, obj):
        return obj.course.name


@admin.register(ExamBlueprintDomainRule)
class ExamBlueprintDomainRuleAdmin(admin.ModelAdmin):
    list_display = ["blueprint_title", "domain_name", "number_of_questions"]

    def blueprint_title(self, obj):
        return obj.blueprint.title

    def domain_name(self, obj):
        return obj.domain.name


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["user_username", "action", "entity_type", "entity_id", "timestamp"]
    list_filter = ["action", "entity_type"]
    search_fields = ["description"]
    ordering = ["-timestamp"]

    def user_username(self, obj):
        return obj.user.username if obj.user else "System"


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False
