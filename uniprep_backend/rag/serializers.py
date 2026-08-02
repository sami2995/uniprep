from rest_framework import serializers
from .models import (
    StudyMaterial,
    DocumentChunk,
    AIChatSession,
    AIChatMessage,
    MaterialSummary,
    GeneratedFlashcard,
    GeneratedQuiz,
    GeneratedQuizQuestion
)


class StudyMaterialSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True, default=None)
    domain_name = serializers.CharField(source="domain.name", read_only=True, default=None)
    topic_name = serializers.CharField(source="topic.name", read_only=True, default=None)
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True, default=None)
    chunk_count = serializers.SerializerMethodField()
    has_summary = serializers.SerializerMethodField()
    has_flashcards = serializers.SerializerMethodField()
    has_quiz = serializers.SerializerMethodField()

    class Meta:
        model = StudyMaterial
        fields = "__all__"
        read_only_fields = [
            "owner",
            "processing_status",
            "error_message",
            "uploaded_at"
        ]

    def get_chunk_count(self, obj):
        return obj.chunks.count()

    def get_has_summary(self, obj):
        return hasattr(obj, "summary") and obj.summary is not None

    def get_has_flashcards(self, obj):
        return obj.flashcards.exists()

    def get_has_quiz(self, obj):
        return obj.generated_quizzes.exists()


class DocumentChunkSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = DocumentChunk
        fields = "__all__"


class AIChatMessageSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = AIChatMessage
        fields = "__all__"


class AIChatSessionSerializer(
    serializers.ModelSerializer
):
    messages = AIChatMessageSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = AIChatSession
        fields = "__all__"


class MaterialSummarySerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = MaterialSummary
        fields = "__all__"


class GeneratedFlashcardSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = GeneratedFlashcard
        fields = "__all__"


class GeneratedQuizQuestionSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = GeneratedQuizQuestion
        fields = "__all__"


class GeneratedQuizSerializer(
    serializers.ModelSerializer
):
    questions = GeneratedQuizQuestionSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = GeneratedQuiz
        fields = "__all__"