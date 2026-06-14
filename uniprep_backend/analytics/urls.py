from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudentTopicPerformanceViewSet,
    SpacedRepetitionQueueViewSet,
    ReadinessScoreViewSet,
    student_dashboard,
    start_focus_session,
    end_focus_session,
    focus_summary
)


router = DefaultRouter()

router.register("topic-performance", StudentTopicPerformanceViewSet, basename="topic-performance")
router.register("spaced-repetition", SpacedRepetitionQueueViewSet, basename="spaced-repetition")
router.register("readiness-scores", ReadinessScoreViewSet, basename="readiness-scores")

urlpatterns = [
    path("dashboard/", student_dashboard, name="student-dashboard"),
    path("focus/start/", start_focus_session, name="start-focus-session"),
    path("focus/end/", end_focus_session, name="end-focus-session"),
    path("focus/summary/", focus_summary, name="focus-summary"),
    path("", include(router.urls)),
]