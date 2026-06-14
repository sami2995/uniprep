from rest_framework import serializers
from .models import (
    Course,
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
    ExamBlueprintDomainRule
)


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"


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

    class Meta:
        model = Topic
        fields = "__all__"


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = "__all__"


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(
        many=True,
        read_only=True
    )

    topic_name = serializers.CharField(
        source="topic.name",
        read_only=True
    )

    class Meta:
        model = Question
        fields = "__all__"


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

    domain_rules = ExamBlueprintDomainRuleSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = ExamBlueprint
        fields = "__all__"