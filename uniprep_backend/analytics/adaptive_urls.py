from django.urls import path
from .views_adaptive import (
    current_learning_path,
    start_learning_path,
    complete_learning_step,
    finish_learning_path_view,
    topic_summary_view,
    topic_flashcards_view,
    adaptive_quiz_questions,
    submit_adaptive_quiz,
    complete_mini_mock_step,
)

urlpatterns = [
    path("current/", current_learning_path, name="adaptive-current"),
    path("start/", start_learning_path, name="adaptive-start"),
    path("step-complete/", complete_learning_step, name="adaptive-step-complete"),
    path("finish/", finish_learning_path_view, name="adaptive-finish"),
    path("summary/", topic_summary_view, name="adaptive-summary"),
    path("flashcards/", topic_flashcards_view, name="adaptive-flashcards"),
    path("quiz/", adaptive_quiz_questions, name="adaptive-quiz-questions"),
    path("quiz/submit/", submit_adaptive_quiz, name="adaptive-quiz-submit"),
    path("mini-mock/complete/", complete_mini_mock_step, name="adaptive-mini-mock-complete"),
]
