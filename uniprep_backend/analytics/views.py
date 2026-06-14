from datetime import timedelta
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import StudentTopicPerformance, SpacedRepetitionQueue, ReadinessScore , FocusSession
from .serializers import (
    StudentTopicPerformanceSerializer,
    SpacedRepetitionQueueSerializer,
    ReadinessScoreSerializer,
    FocusSessionSerializer
)


class StudentTopicPerformanceViewSet(viewsets.ModelViewSet):
    serializer_class = StudentTopicPerformanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return StudentTopicPerformance.objects.all()
        return StudentTopicPerformance.objects.filter(student=user)


class SpacedRepetitionQueueViewSet(viewsets.ModelViewSet):
    serializer_class = SpacedRepetitionQueueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return SpacedRepetitionQueue.objects.all()
        return SpacedRepetitionQueue.objects.filter(student=user)


class ReadinessScoreViewSet(viewsets.ModelViewSet):
    serializer_class = ReadinessScoreSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return ReadinessScore.objects.all()
        return ReadinessScore.objects.filter(student=user)




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_dashboard(request):
    user = request.user

    if user.role != "student":
        return Response(
            {"detail": "Only students can view this dashboard."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Readiness scores
    readiness_scores = ReadinessScore.objects.filter(
        student=user
    ).select_related("course")

    # Topic performance
    topic_performances = StudentTopicPerformance.objects.filter(
        student=user
    ).select_related("domain", "topic")

    # Weak topics: accuracy below 60%
    weak_topics = [
        {
            "topic_id": performance.topic.id,
            "topic": performance.topic.name,
            "domain": performance.domain.name,
            "accuracy": performance.accuracy,
            "correct_attempts": performance.correct_attempts,
            "total_attempts": performance.total_attempts
        }
        for performance in topic_performances
        if performance.total_attempts > 0 and performance.accuracy < 60
    ]

    # Spaced repetition due today or earlier
    due_reviews = SpacedRepetitionQueue.objects.filter(
        student=user,
        is_active=True,
        next_review_date__lte=timezone.now().date()
    ).select_related("question", "topic")

    # Focus / productivity summary
    today = timezone.now().date()
    week_start = today - timedelta(days=6)

    focus_sessions = FocusSession.objects.filter(
        student=user,
        ended_at__isnull=False
    )

    today_focus_minutes = sum(
        session.duration_minutes
        for session in focus_sessions
        if session.started_at.date() == today
    )

    week_focus_minutes = sum(
        session.duration_minutes
        for session in focus_sessions
        if session.started_at.date() >= week_start
    )

    recent_focus_sessions = focus_sessions.select_related(
        "course", "topic"
    ).order_by("-started_at")[:5]

    return Response(
        {
            "readiness_scores": [
                {
                    "course_id": item.course.id,
                    "course": item.course.name,
                    "score": item.score,
                    "calculated_at": item.calculated_at
                }
                for item in readiness_scores
            ],

            "topic_performance": [
                {
                    "topic_id": performance.topic.id,
                    "topic": performance.topic.name,
                    "domain": performance.domain.name,
                    "accuracy": performance.accuracy,
                    "correct_attempts": performance.correct_attempts,
                    "total_attempts": performance.total_attempts
                }
                for performance in topic_performances
            ],

            "weak_topics": weak_topics,

            "spaced_repetition_due": [
                {
                    "id": item.id,
                    "question_id": item.question.id,
                    "question": item.question.text,
                    "topic": item.topic.name,
                    "next_review_date": item.next_review_date,
                    "mastery_level": item.mastery_level
                }
                for item in due_reviews
            ],

            "focus_summary": {
                "today_minutes": today_focus_minutes,
                "week_minutes": week_focus_minutes,
                "recent_sessions": [
                    {
                        "id": session.id,
                        "course": session.course.name if session.course else None,
                        "topic": session.topic.name if session.topic else None,
                        "started_at": session.started_at,
                        "ended_at": session.ended_at,
                        "duration_minutes": session.duration_minutes
                    }
                    for session in recent_focus_sessions
                ]
            }
        },
        status=status.HTTP_200_OK
    )
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_focus_session(request):
    user = request.user

    if user.role != "student":
        return Response(
            {"detail": "Only students can start focus sessions."},
            status=status.HTTP_403_FORBIDDEN
        )

    course_id = request.data.get("course_id")
    topic_id = request.data.get("topic_id")

    active_session = FocusSession.objects.filter(
        student=user,
        ended_at__isnull=True
    ).first()

    if active_session:
        return Response(
            {
                "detail": "You already have an active focus session.",
                "session_id": active_session.id
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    session = FocusSession.objects.create(
        student=user,
        course_id=course_id,
        topic_id=topic_id
    )

    return Response(
        {
            "message": "Focus session started.",
            "session_id": session.id,
            "started_at": session.started_at
        },
        status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_focus_session(request):
    user = request.user
    session_id = request.data.get("session_id")

    if not session_id:
        return Response(
            {"detail": "session_id is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        session = FocusSession.objects.get(
            id=session_id,
            student=user,
            ended_at__isnull=True
        )
    except FocusSession.DoesNotExist:
        return Response(
            {"detail": "Active focus session not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    session.ended_at = timezone.now()

    seconds = (session.ended_at - session.started_at).total_seconds()
    session.duration_minutes = max(1, int(seconds // 60))

    session.save()

    return Response(
        {
            "message": "Focus session ended.",
            "session_id": session.id,
            "duration_minutes": session.duration_minutes
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def focus_summary(request):
    user = request.user

    today = timezone.now().date()
    week_start = today - timedelta(days=6)

    sessions = FocusSession.objects.filter(
        student=user,
        ended_at__isnull=False
    ).select_related("course", "topic")

    today_minutes = sum(
        session.duration_minutes
        for session in sessions
        if session.started_at.date() == today
    )

    week_minutes = sum(
        session.duration_minutes
        for session in sessions
        if session.started_at.date() >= week_start
    )

    recent_sessions = sessions.order_by("-started_at")[:10]
    active_session = FocusSession.objects.filter(
        student=user,
        ended_at__isnull=True
    ).first()

    return Response(
        {
            "today_minutes": today_minutes,
            "week_minutes": week_minutes,
            "active_session": {
                "id": active_session.id,
                "started_at": active_session.started_at
            } if active_session else None,
            "recent_sessions": [
                {
                    "id": session.id,
                    "course": session.course.name if session.course else None,
                    "topic": session.topic.name if session.topic else None,
                    "started_at": session.started_at,
                    "ended_at": session.ended_at,
                    "duration_minutes": session.duration_minutes
                }
                for session in recent_sessions
            ]
        },
        status=status.HTTP_200_OK
    )
