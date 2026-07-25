from rest_framework import serializers
from .models import (
    Department,
    Course,
    TeacherCourseAssignment,
    Domain,
    Topic,
    Question,
    Choice,
    MockExam,
    MockExamQuestion,
    ExamAttempt,
    AttemptDetail,
    ExamPdfImport,
    ExtractedQuestion,
    ExamBlueprint,
    ExamBlueprintDomainRule,
    AuditLog,
)


class DepartmentSerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Department
        fields = ["id", "name", "code", "description", "created_at", "course_count"]
        read_only_fields = ["created_at", "course_count"]


class CourseSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
        default=""
    )

    class Meta:
        model = Course
        fields = "__all__"


class TeacherCourseAssignmentSerializer(serializers.ModelSerializer):
    teacher_username = serializers.CharField(
        source="teacher.username",
        read_only=True
    )
    course_name = serializers.CharField(
        source="course.name",
        read_only=True
    )

    class Meta:
        model = TeacherCourseAssignment
        fields = "__all__"
        read_only_fields = ["assigned_at"]

    def validate_teacher(self, teacher):
        if getattr(teacher, "role", None) != "teacher":
            raise serializers.ValidationError(
                "Only TEACHER users can be assigned to courses."
            )
        return teacher


class DomainSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(
        source="course.name",
        read_only=True
    )

    class Meta:
        model = Domain
        fields = "__all__"


class TopicSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(
        source="domain.name",
        read_only=True
    )
    domain_course_id = serializers.IntegerField(
        source="domain.course.id",
        read_only=True
    )

    class Meta:
        model = Topic
        fields = "__all__"


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = "__all__"


class QuestionChoiceWriteSerializer(serializers.Serializer):
    text = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)
    is_correct = serializers.BooleanField(default=False)


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(
        many=True,
        read_only=True
    )
    choice_inputs = QuestionChoiceWriteSerializer(
        many=True,
        write_only=True,
        required=False
    )
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
        default=""
    )
    reviewed_by_username = serializers.CharField(
        source="reviewed_by.username",
        read_only=True,
        default=""
    )

    topic_name = serializers.CharField(
        source="topic.name",
        read_only=True
    )
    domain_name = serializers.CharField(
        source="topic.domain.name",
        read_only=True
    )
    course_name = serializers.CharField(
        source="topic.domain.course.name",
        read_only=True
    )
    department_name = serializers.CharField(
        source="topic.domain.course.department.name",
        read_only=True,
        default=""
    )

    class Meta:
        model = Question
        fields = "__all__"
        read_only_fields = [
            "created_by",
            "reviewed_by",
            "uploaded_by",
            "approved_by",
            "approved_at",
            "originating_pdf_import",
            "source_type",
            "reviewed_at",
            "rejection_reason",
            "submitted_at",
            "status",
        ]

    def validate_choice_inputs(self, choices):
        if len(choices) != 4:
            raise serializers.ValidationError("Exactly four choices are required.")

        correct_count = sum(1 for choice in choices if choice.get("is_correct"))
        if correct_count != 1:
            raise serializers.ValidationError("Exactly one choice must be marked correct.")

        for choice in choices:
            text = str(choice.get("text", "")).strip()
            if not text:
                raise serializers.ValidationError("Choice text cannot be blank.")

        return choices

    def validate(self, attrs):
        initial_choices = self.initial_data.get("choices") or self.initial_data.get("choice_inputs")
        if initial_choices is not None:
            if not isinstance(initial_choices, list) or len(initial_choices) != 4:
                raise serializers.ValidationError({"choices": "Exactly four choices are required."})

            correct_count = 0
            formatted_choices = []
            for i, choice in enumerate(initial_choices):
                if not isinstance(choice, dict):
                    raise serializers.ValidationError({"choices": "Each choice must be an object."})
                text = str(choice.get("text", "")).strip()
                if not text:
                    raise serializers.ValidationError({"choices": f"Choice {i+1} text cannot be blank."})
                is_correct = bool(choice.get("is_correct", False))
                if is_correct:
                    correct_count += 1
                formatted_choices.append({"text": text, "is_correct": is_correct})

            if correct_count != 1:
                raise serializers.ValidationError({"choices": "Exactly one choice must be marked correct."})

            attrs["_validated_choices"] = formatted_choices
        return attrs


class RejectQuestionSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True
    )


class MockExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockExam
        fields = "__all__"


class MockExamQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockExamQuestion
        fields = "__all__"


class AttemptDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttemptDetail
        fields = "__all__"


class ExamAttemptSerializer(serializers.ModelSerializer):
    details = AttemptDetailSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = ExamAttempt
        fields = "__all__"


class StudentChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text"]


class StudentQuestionSerializer(serializers.ModelSerializer):
    choices = StudentChoiceSerializer(many=True, read_only=True)
    topic_name = serializers.CharField(source="topic.name", read_only=True)
    domain_name = serializers.CharField(source="topic.domain.name", read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "bloom_level",
            "difficulty",
            "topic_name",
            "domain_name",
            "choices"
        ]


class MockExamQuestionDetailSerializer(serializers.ModelSerializer):
    question = StudentQuestionSerializer(read_only=True)

    class Meta:
        model = MockExamQuestion
        fields = ["id", "order", "question"]


class MockExamDetailSerializer(serializers.ModelSerializer):
    mock_questions = MockExamQuestionDetailSerializer(many=True, read_only=True)

    class Meta:
        model = MockExam
        fields = [
            "id",
            "title",
            "exam_number",
            "total_questions",
            "duration_minutes",
            "status",
            "generated_at",
            "mock_questions"
        ]


class ExamPdfImportSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username",
        read_only=True
    )

    class Meta:
        model = ExamPdfImport
        fields = "__all__"
        read_only_fields = [
            "uploaded_by",
            "status",
            "extracted_text",
            "error_message",
            "uploaded_at"
        ]


class ExtractedQuestionSerializer(serializers.ModelSerializer):
    import_title = serializers.CharField(
        source="exam_import.title",
        read_only=True
    )
    course = serializers.IntegerField(
        source="exam_import.course.id",
        read_only=True
    )
    course_name = serializers.CharField(
        source="exam_import.course.name",
        read_only=True
    )
    uploaded_by_username = serializers.CharField(
        source="exam_import.uploaded_by.username",
        read_only=True,
        default=""
    )

    class Meta:
        model = ExtractedQuestion
        fields = "__all__"
        read_only_fields = [
            "status",
            "approved_question",
            "created_at"
        ]


class ExamBlueprintDomainRuleSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(
        source="domain.name",
        read_only=True
    )

    class Meta:
        model = ExamBlueprintDomainRule
        fields = "__all__"


class ExamBlueprintSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(
        source="course.name",
        read_only=True
    )
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
        default=""
    )
    domain_rules = ExamBlueprintDomainRuleSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = ExamBlueprint
        fields = "__all__"
        read_only_fields = ["created_at", "created_by"]


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
        default="System"
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "username",
            "action",
            "entity_type",
            "entity_id",
            "timestamp",
            "previous_value",
            "new_value",
            "description",
        ]
        read_only_fields = fields


class DuplicateCheckSerializer(serializers.Serializer):
    text = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )
    course_id = serializers.IntegerField(required=False, allow_null=True)
    exclude_question_id = serializers.IntegerField(required=False, allow_null=True)
    threshold = serializers.FloatField(
        required=False,
        default=0.85,
        min_value=0.0,
        max_value=1.0,
    )
