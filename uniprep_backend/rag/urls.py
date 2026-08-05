from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    StudyMaterialViewSet,
    DocumentChunkViewSet,
    AIChatSessionViewSet,
    AIChatMessageViewSet,
    MaterialSummaryViewSet,
    GeneratedFlashcardViewSet,
    GeneratedQuizViewSet,
    GeneratedQuizQuestionViewSet,
    process_study_material,
    generate_material_summary,
    ask_material_question,
    generate_material_flashcards,
    generate_material_quiz,
    get_material_quiz,
    get_material_chat,
    submit_material_quiz,
    get_material_quiz_attempt,
)


router = DefaultRouter()

router.register("materials", StudyMaterialViewSet, basename="materials")
router.register("chunks", DocumentChunkViewSet, basename="chunks")
router.register("chat-sessions", AIChatSessionViewSet, basename="chat-sessions")
router.register("chat-messages", AIChatMessageViewSet, basename="chat-messages")
router.register("summaries", MaterialSummaryViewSet, basename="summaries")
router.register("flashcards", GeneratedFlashcardViewSet, basename="flashcards")
router.register("generated-quizzes", GeneratedQuizViewSet, basename="generated-quizzes")
router.register(
    "generated-quiz-questions",
    GeneratedQuizQuestionViewSet,
    basename="generated-quiz-questions"
)

urlpatterns = [
    path(
        "materials/<int:material_id>/process/",
        process_study_material,
        name="process-study-material"
    ),
    path(
        "materials/<int:material_id>/summary/",
        generate_material_summary,
        name="generate-material-summary"
    ),
    path(
        "materials/<int:material_id>/ask/",
        ask_material_question,
        name="ask-material-question"
    ),
    path(
        "materials/<int:material_id>/flashcards/",
        generate_material_flashcards,
        name="generate-material-flashcards"
    ),
    path(
        "materials/<int:material_id>/generate-quiz/",
        generate_material_quiz,
        name="generate-material-quiz"
    ),
    path(
        "materials/<int:material_id>/quiz/",
        get_material_quiz,
        name="get-material-quiz"
    ),
    path(
        "materials/<int:material_id>/quiz/submit/",
        submit_material_quiz,
        name="submit-material-quiz"
    ),
    path(
        "materials/<int:material_id>/quiz/attempts/<int:attempt_id>/",
        get_material_quiz_attempt,
        name="get-material-quiz-attempt"
    ),
    path(
        "materials/<int:material_id>/chat/",
        get_material_chat,
        name="get-material-chat"
    ),
    path("", include(router.urls)),
]