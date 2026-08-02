import random

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from exit_exams.models import Course, Question, Choice

from .models import (
    QuizChallenge,
    ChallengeParticipant,
    ChallengeQuestion,
    ChallengeAttempt,
    ChallengeAttemptDetail,
    generate_challenge_code,
)

from .serializers import (
    QuizChallengeSerializer,
    ChallengeParticipantSerializer,
    ChallengeQuestionSerializer,
    ChallengeAttemptSerializer,
)


def is_student(user):
    return getattr(user, "role", None) == "student"


def generate_unique_challenge_code():
    code = generate_challenge_code()

    while QuizChallenge.objects.filter(room_code=code).exists():
        code = generate_challenge_code()

    return code


def get_challenge_or_none(room_code):
    return QuizChallenge.objects.filter(
        room_code=room_code.upper()
    ).select_related("course", "created_by").first()


def is_participant(challenge, user):
    return ChallengeParticipant.objects.filter(
        challenge=challenge,
        student=user
    ).exists()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_challenge(request):
    user = request.user

    if not is_student(user):
        return Response(
            {"detail": "Only students can create challenge rooms."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        course_id = request.data.get("course_id")
        title = request.data.get("title", "Quiz Challenge")
        total_questions = int(request.data.get("total_questions", 5))
        duration_minutes = int(request.data.get("duration_minutes", 10))

        if not course_id:
            return Response(
                {"detail": "course_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        course = Course.objects.filter(id=course_id).first()

        if not course:
            return Response(
                {"detail": "Course not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        approved_questions = list(
            Question.objects.filter(
                topic__domain__course=course,
                is_active=True,
                status=Question.Status.APPROVED
            ).prefetch_related("choices").distinct()
        )

        if len(approved_questions) < total_questions:
            return Response(
                {
                    "detail": (
                        f"Not enough approved questions for this course. "
                        f"Available: {len(approved_questions)}, requested: {total_questions}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        selected_questions = random.sample(approved_questions, total_questions)

        with transaction.atomic():
            challenge = QuizChallenge.objects.create(
                room_code=generate_unique_challenge_code(),
                title=title,
                course=course,
                created_by=user,
                total_questions=total_questions,
                duration_minutes=duration_minutes,
                status=QuizChallenge.Status.WAITING
            )

            ChallengeParticipant.objects.create(
                challenge=challenge,
                student=user,
                is_creator=True
            )

            for index, question in enumerate(selected_questions, start=1):
                ChallengeQuestion.objects.create(
                    challenge=challenge,
                    question=question,
                    order=index
                )

        return Response(
            {
                "message": "Challenge room created successfully.",
                "room": QuizChallengeSerializer(challenge).data,
            },
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(
            {"detail": f"Error creating challenge: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_challenge(request):
    user = request.user

    if not is_student(user):
        return Response(
            {"detail": "Only students can join challenge rooms."},
            status=status.HTTP_403_FORBIDDEN
        )

    room_code = request.data.get("room_code", "").strip().upper()

    if not room_code:
        return Response(
            {"detail": "room_code is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    challenge = get_challenge_or_none(room_code)

    if not challenge:
        return Response(
            {"detail": "Challenge room not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if challenge.status != QuizChallenge.Status.WAITING:
        return Response(
            {"detail": "This challenge is not open for joining."},
            status=status.HTTP_400_BAD_REQUEST
        )

    participant, created = ChallengeParticipant.objects.get_or_create(
        challenge=challenge,
        student=user,
        defaults={"is_creator": False}
    )

    return Response(
        {
            "message": "Joined challenge room successfully.",
            "room": QuizChallengeSerializer(challenge).data,
            "participant": ChallengeParticipantSerializer(participant).data,
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def challenge_detail(request, room_code):
    user = request.user
    challenge = get_challenge_or_none(room_code)

    if not challenge:
        return Response(
            {"detail": "Challenge room not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if not is_participant(challenge, user):
        return Response(
            {"detail": "You are not a participant in this challenge."},
            status=status.HTTP_403_FORBIDDEN
        )

    participants = ChallengeParticipant.objects.filter(
        challenge=challenge
    ).select_related("student")

    return Response(
        {
            "room": QuizChallengeSerializer(challenge).data,
            "participants": ChallengeParticipantSerializer(
                participants,
                many=True
            ).data,
        },
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_challenge(request, room_code):
    user = request.user
    challenge = get_challenge_or_none(room_code)

    if not challenge:
        return Response(
            {"detail": "Challenge room not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if challenge.created_by != user:
        return Response(
            {"detail": "Only the creator can start the challenge."},
            status=status.HTTP_403_FORBIDDEN
        )

    if challenge.status != QuizChallenge.Status.WAITING:
        return Response(
            {"detail": "Challenge already started or completed."},
            status=status.HTTP_400_BAD_REQUEST
        )

    challenge.status = QuizChallenge.Status.ACTIVE
    challenge.started_at = timezone.now()
    challenge.save()

    return Response(
        {
            "message": "Challenge started successfully.",
            "room": QuizChallengeSerializer(challenge).data,
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def challenge_questions(request, room_code):
    user = request.user
    challenge = get_challenge_or_none(room_code)

    if not challenge:
        return Response(
            {"detail": "Challenge room not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if not is_participant(challenge, user):
        return Response(
            {"detail": "You are not a participant in this challenge."},
            status=status.HTTP_403_FORBIDDEN
        )

    if challenge.status != QuizChallenge.Status.ACTIVE:
        return Response(
            {"detail": "Challenge has not started yet."},
            status=status.HTTP_400_BAD_REQUEST
        )

    questions = ChallengeQuestion.objects.filter(
        challenge=challenge
    ).select_related("question").prefetch_related("question__choices")

    return Response(
        {
            "room": QuizChallengeSerializer(challenge).data,
            "questions": ChallengeQuestionSerializer(questions, many=True).data,
        },
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_challenge(request, room_code):
    user = request.user
    challenge = get_challenge_or_none(room_code)

    if not challenge:
        return Response(
            {"detail": "Challenge room not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if not is_participant(challenge, user):
        return Response(
            {"detail": "You are not a participant in this challenge."},
            status=status.HTTP_403_FORBIDDEN
        )

    if challenge.status != QuizChallenge.Status.ACTIVE:
        return Response(
            {"detail": "Challenge is not active."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if ChallengeAttempt.objects.filter(challenge=challenge, student=user).exists():
        return Response(
            {"detail": "You already submitted this challenge."},
            status=status.HTTP_400_BAD_REQUEST
        )

    answers = request.data.get("answers", [])
    duration_seconds = int(request.data.get("duration_seconds", 0))

    answer_map = {
        int(item["question_id"]): item.get("selected_choice_id")
        for item in answers
        if item.get("question_id")
    }

    challenge_questions_qs = ChallengeQuestion.objects.filter(
        challenge=challenge
    ).select_related("question").prefetch_related("question__choices")

    total = challenge_questions_qs.count()
    correct_count = 0

    with transaction.atomic():
        attempt = ChallengeAttempt.objects.create(
            challenge=challenge,
            student=user,
            duration_seconds=duration_seconds,
            submitted_at=timezone.now()
        )

        for item in challenge_questions_qs:
            question = item.question
            selected_choice_id = answer_map.get(question.id)

            selected_choice = None

            if selected_choice_id:
                selected_choice = Choice.objects.filter(
                    id=selected_choice_id,
                    question=question
                ).first()

            correct_choice = question.choices.filter(is_correct=True).first()

            is_correct_answer = (
                selected_choice is not None
                and correct_choice is not None
                and selected_choice.id == correct_choice.id
            )

            if is_correct_answer:
                correct_count += 1

            ChallengeAttemptDetail.objects.create(
                attempt=attempt,
                question=question,
                selected_choice=selected_choice,
                is_correct=is_correct_answer,
                response_time_seconds=0
            )

        attempt.score = round((correct_count / total) * 100, 2) if total else 0
        attempt.save()

    return Response(
        {
            "message": "Challenge submitted successfully.",
            "attempt": ChallengeAttemptSerializer(attempt).data,
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def challenge_leaderboard(request, room_code):
    user = request.user
    challenge = get_challenge_or_none(room_code)

    if not challenge:
        return Response(
            {"detail": "Challenge room not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if not is_participant(challenge, user):
        return Response(
            {"detail": "You are not a participant in this challenge."},
            status=status.HTTP_403_FORBIDDEN
        )

    attempts = ChallengeAttempt.objects.filter(
        challenge=challenge
    ).select_related("student").order_by("-score", "duration_seconds")

    leaderboard = []

    for rank, attempt in enumerate(attempts, start=1):
        leaderboard.append({
            "rank": rank,
            "student_id": attempt.student.id,
            "username": attempt.student.username,
            "score": attempt.score,
            "duration_seconds": attempt.duration_seconds,
            "submitted_at": attempt.submitted_at,
        })

    return Response(
        {
            "room": QuizChallengeSerializer(challenge).data,
            "leaderboard": leaderboard,
        },
        status=status.HTTP_200_OK
    )