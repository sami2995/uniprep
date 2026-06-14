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
    class Meta:
        model = StudyMaterial
        fields = "__all__"
        read_only_fields = [
            "owner",
            "processing_status",
            "error_message",
            "uploaded_at"
        ]


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