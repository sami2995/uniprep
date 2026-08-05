from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudentTopicPerformanceViewSet,
    SpacedRepetitionQueueViewSet,
    ReadinessScoreViewSet,
    student_dashboard,
    student_weakness,
    student_trend,
    student_recommendations,
    course_overview,
    topic_difficulty,
    score_trend,
    at_risk_students,
    start_focus_session,
    end_focus_session,
    focus_summary
)
from .teacher_views import teacher_dashboard


router = DefaultRouter()

router.register("topic-performance", StudentTopicPerformanceViewSet, basename="topic-performance")
router.register("spaced-repetition", SpacedRepetitionQueueViewSet, basename="spaced-repetition")
router.register("readiness-scores", ReadinessScoreViewSet, basename="readiness-scores")

urlpatterns = [
    path("dashboard/", student_dashboard, name="student-dashboard"),
    path("teacher-dashboard/", teacher_dashboard, name="teacher-dashboard"),
    path("student/weakness/", student_weakness, name="student-weakness"),
    path("student/trend/", student_trend, name="student-trend"),
    path("student/recommendations/", student_recommendations, name="student-recommendations"),
    path("course-overview/", course_overview, name="course-overview"),
    path("topic-difficulty/", topic_difficulty, name="topic-difficulty"),
    path("score-trend/", score_trend, name="score-trend"),
    path("at-risk-students/", at_risk_students, name="at-risk-students"),
    path("focus/start/", start_focus_session, name="start-focus-session"),
    path("focus/end/", end_focus_session, name="end-focus-session"),
    path("focus/summary/", focus_summary, name="focus-summary"),
    path("", include(router.urls)),
]
