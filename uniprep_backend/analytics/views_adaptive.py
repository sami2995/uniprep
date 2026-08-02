from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from analytics.models import LearningPath
from analytics.serializers import LearningPathSerializer
from analytics.adaptive_learning_service import (
    generate_learning_path,
    complete_step,
    finish_learning_path,
    get_current_learning_path_topic,
    generate_adaptive_quiz,
    evaluate_adaptive_quiz,
    QUIZ_QUESTION_COUNT,
)
from analytics.adaptive_ai_service import (
    generate_topic_summary,
    generate_topic_flashcards,
)
from exit_exams.models import Topic, MockExam, ExamAttempt


def is_student(user):
    return getattr(user, "role", None) == "student"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_learning_path(request):
    user = request.user
    if not is_student(user):
        return Response(
            {"detail": "Only students can view adaptive learning paths."},
            status=status.HTTP_403_FORBIDDEN
        )

    path = LearningPath.objects.filter(student=user, status="in_progress").first()
    if not path:
        return Response(
            {"detail": "No active learning path found.", "learning_path": None},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = LearningPathSerializer(path)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_learning_path(request):
    user = request.user
    if not is_student(user):
        return Response(
            {"detail": "Only students can start an adaptive learning path."},
            status=status.HTTP_403_FORBIDDEN
        )

    path = generate_learning_path(user)
    serializer = LearningPathSerializer(path)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_learning_step(request):
    user = request.user
    if not is_student(user):
        return Response(
            {"detail": "Only students can complete learning steps."},
            status=status.HTTP_403_FORBIDDEN
        )

    path_id = request.data.get("learning_path_id")
    step_type = request.data.get("step_type")
    score = request.data.get("score")

    if not path_id or not step_type:
        return Response(
            {"detail": "learning_path_id and step_type are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        path = LearningPath.objects.get(id=path_id, student=user)
    except LearningPath.DoesNotExist:
        return Response(
            {"detail": "Learning path not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    updated_path, unlocked, message = complete_step(path, step_type, score)
    serializer = LearningPathSerializer(updated_path)

    res_status = status.HTTP_200_OK if unlocked else status.HTTP_400_BAD_REQUEST
    return Response({
        "message": message,
        "unlocked": unlocked,
        "learning_path": serializer.data
    }, status=res_status)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def finish_learning_path_view(request):
    user = request.user
    if not is_student(user):
        return Response(
            {"detail": "Only students can finish an adaptive learning path."},
            status=status.HTTP_403_FORBIDDEN
        )

    path_id = request.data.get("learning_path_id")
    if not path_id:
        return Response(
            {"detail": "learning_path_id is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        path = LearningPath.objects.get(id=path_id, student=user)
    except LearningPath.DoesNotExist:
        return Response(
            {"detail": "Learning path not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    result, err = finish_learning_path(path)
    if err:
        return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

    return Response(result, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def topic_summary_view(request):
    """
    GET /api/adaptive-learning/summary/?topic=<topic_name>
         OR ?topic_id=<id>

    Returns an AI-generated structured summary for a topic,
    sourced from the approved exam bank questions (NOT from uploaded materials).

    Summary step of the Adaptive Learning path.
    """
    user = request.user
    if not is_student(user):
        return Response(
            {"detail": "Only students can access adaptive learning content."},
            status=status.HTTP_403_FORBIDDEN
        )

    topic_id = request.query_params.get("topic_id")
    topic_name = request.query_params.get("topic")

    topic_obj = None
    if topic_id:
        topic_obj = Topic.objects.filter(id=topic_id).first()
    elif topic_name:
        topic_obj = Topic.objects.filter(name__iexact=topic_name.strip()).first()

    if not topic_obj:
        return Response(
            {"detail": "Topic not found. Provide topic_id or topic name."},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        summary = generate_topic_summary(topic_obj)
    except Exception as exc:
        return Response(
            {"detail": f"Failed to generate summary: {str(exc)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return Response({
        "topic": topic_obj.name,
        "domain": topic_obj.domain.name,
        "summary_text": summary["summary_text"],
        "key_points": summary["key_points"],
        "important_terms": summary["important_terms"],
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def topic_flashcards_view(request):
    """
    GET /api/adaptive-learning/flashcards/?topic=<topic_name>&count=10
         OR ?topic_id=<id>&count=10

    Returns AI-generated flashcards for a topic, weighted toward the student's
    actual gaps (unseen questions first, then incorrectly-answered, then known).

    Flashcards step of the Adaptive Learning path.
    Quiz and Mini Mock steps remain AI-FREE (direct exam bank question selection).
    """
    user = request.user
    if not is_student(user):
        return Response(
            {"detail": "Only students can access adaptive learning content."},
            status=status.HTTP_403_FORBIDDEN
        )

    topic_id = request.query_params.get("topic_id")
    topic_name = request.query_params.get("topic")

    try:
        count = int(request.query_params.get("count", 10))
        count = max(3, min(count, 20))  # Clamp between 3 and 20
    except (TypeError, ValueError):
        count = 10

    topic_obj = None
    if topic_id:
        topic_obj = Topic.objects.filter(id=topic_id).first()
    elif topic_name:
        topic_obj = Topic.objects.filter(name__iexact=topic_name.strip()).first()

    if not topic_obj:
        return Response(
            {"detail": "Topic not found. Provide topic_id or topic name."},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        flashcards = generate_topic_flashcards(topic_obj, student=user, count=count)
    except Exception as exc:
        return Response(
            {"detail": f"Failed to generate flashcards: {str(exc)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return Response({
        "topic": topic_obj.name,
        "domain": topic_obj.domain.name,
        "count": len(flashcards),
        "flashcards": flashcards,
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def adaptive_quiz_questions(request):
    """
    GET /api/adaptive-learning/quiz/

    Returns approved active quiz questions for the student's current
    adaptive learning path topic. Inline step for AdaptiveLearningPage.
    """
    user = request.user
    if not is_student(user):
        return Response(
            {"detail": "Only students can take adaptive quizzes."},
            status=status.HTTP_403_FORBIDDEN
        )

    path = get_current_learning_path_topic(user)
    if not path:
        return Response(
            {"detail": "No active learning path found."},
            status=status.HTTP_404_NOT_FOUND
        )

    topic_obj = Topic.objects.filter(name=path.topic).first()
    if not topic_obj:
        return Response(
            {"detail": "Topic not found for current learning path."},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        count = int(request.query_params.get("count", QUIZ_QUESTION_COUNT))
        count = max(1, min(count, 20))
    except (TypeError, ValueError):
        count = QUIZ_QUESTION_COUNT

    try:
        selected = generate_adaptive_quiz(user, topic_obj, count=count)
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )

    from exit_exams.serializers import StudentQuestionSerializer
    serializer = StudentQuestionSerializer(selected, many=True)

    return Response({
        "topic": topic_obj.name,
        "topic_id": topic_obj.id,
        "count": len(selected),
        "questions": serializer.data,
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_adaptive_quiz(request):
    """
    POST /api/adaptive-learning/quiz/submit/

    Submits answers for the current adaptive learning path topic quiz.
    Backend calculates the real score; frontend-submitted scores are ignored.
    """
    user = request.user
    if not is_student(user):
        return Response(
            {"detail": "Only students can submit adaptive quizzes."},
            status=status.HTTP_403_FORBIDDEN
        )

    path = get_current_learning_path_topic(user)
    if not path:
        return Response(
            {"detail": "No active learning path found."},
            status=status.HTTP_404_NOT_FOUND
        )

    topic_obj = Topic.objects.filter(name=path.topic).first()
    if not topic_obj:
        return Response(
            {"detail": "Topic not found for current learning path."},
            status=status.HTTP_404_NOT_FOUND
        )

    answers = request.data.get("answers", [])
    if not isinstance(answers, list):
        return Response(
            {"detail": "answers must be a list."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Reject any frontend-provided score; only answers are accepted.
    if "score" in request.data:
        return Response(
            {"detail": "Frontend-provided scores are not accepted."},
            status=status.HTTP_400_BAD_REQUEST
        )

    duration_seconds = int(request.data.get("duration_seconds", 0))

    try:
        result = evaluate_adaptive_quiz(user, topic_obj, answers, duration_seconds)
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response(result, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_mini_mock_step(request):
    """
    POST /api/adaptive-learning/mini-mock/complete/

    Marks the mini_mock learning step complete only after a real submitted
    Mini Mock attempt exists for the current adaptive path topic.
    """
    user = request.user
    if not is_student(user):
        return Response(
            {"detail": "Only students can complete mini mock steps."},
            status=status.HTTP_403_FORBIDDEN
        )

    path = get_current_learning_path_topic(user)
    if not path:
        return Response(
            {"detail": "No active learning path found."},
            status=status.HTTP_404_NOT_FOUND
        )

    topic_obj = Topic.objects.filter(name=path.topic).first()
    if not topic_obj:
        return Response(
            {"detail": "Topic not found for current learning path."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Verify a real submitted Mini Mock attempt exists for this topic.
    has_submitted_attempt = ExamAttempt.objects.filter(
        student=user,
        mock_exam__course=topic_obj.domain.course,
        mock_exam__title__icontains="Mini Mock",
        mock_exam__mock_questions__question__topic=topic_obj,
        status=ExamAttempt.Status.SUBMITTED
    ).exists()

    if not has_submitted_attempt:
        return Response(
            {"detail": "No submitted mini mock found for this topic."},
            status=status.HTTP_400_BAD_REQUEST
        )

    updated_path, unlocked, message = complete_step(path, "mini_mock")
    serializer = LearningPathSerializer(updated_path)

    return Response({
        "message": message,
        "unlocked": unlocked,
        "learning_path": serializer.data
    }, status=status.HTTP_200_OK)
