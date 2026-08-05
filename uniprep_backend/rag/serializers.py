from rest_framework import serializers
from .models import (
    StudyMaterial,
    DocumentChunk,
    AIChatSession,
    AIChatMessage,
    MaterialSummary,
    GeneratedFlashcard,
    GeneratedQuiz,
    GeneratedQuizQuestion,
    MaterialQuizAttempt,
    MaterialQuizAnswer,
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


class GeneratedQuizQuestionFetchSerializer(
    serializers.ModelSerializer
):
    """Student-facing quiz question serializer.

    Omits ``correct_answer`` and ``explanation`` so that the correct
    answer / reasoning are not shipped to the client before the student
    has actually submitted their attempt. Scoring is performed
    authoritatively on the backend at submit time.
    """

    class Meta:
        model = GeneratedQuizQuestion
        fields = ["id", "question_text", "choices"]


class GeneratedQuizSerializer(
    serializers.ModelSerializer
):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedQuiz
        fields = "__all__"

    def get_questions(self, obj):
        include_answers = self.context.get("include_answers", True)
        qs = obj.questions.all()
        if include_answers:
            return GeneratedQuizQuestionSerializer(qs, many=True).data
        return GeneratedQuizQuestionFetchSerializer(qs, many=True).data


class MaterialQuizAnswerSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = MaterialQuizAnswer
        fields = "__all__"


class MaterialQuizAttemptSerializer(
    serializers.ModelSerializer
):
    answers = MaterialQuizAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = MaterialQuizAttempt
        fields = "__all__"