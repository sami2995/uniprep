from .permissions import IsAdminRole, IsAdminOrReadOnly
import random

from django.db import transaction
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count
from analytics.models import ReadinessScore, StudentTopicPerformance

from .models import (
    Course,
    Domain,
    Topic,
    Question,
    Choice,
    MockExam,
    MockExamQuestion,
    ExamAttempt,
    AttemptDetail,
    ExamPdfImport,
    ExtractedQuestion,
    ExamBlueprint,
    ExamBlueprintDomainRule,
)

from .serializers import (
    CourseSerializer,
    DomainSerializer,
    TopicSerializer,
    QuestionSerializer,
    ChoiceSerializer,
    MockExamSerializer,
    MockExamQuestionSerializer,
    ExamAttemptSerializer,
    AttemptDetailSerializer,
    MockExamDetailSerializer,
    ExamPdfImportSerializer,
    ExtractedQuestionSerializer,
    ExamBlueprintSerializer,
    ExamBlueprintDomainRuleSerializer,
)

from analytics.services import (
    update_topic_performance,
    add_wrong_question_to_spaced_repetition,
    calculate_readiness_score,
)

from .services.pdf_importer import (
    extract_text_from_pdf,
    is_scanned_or_empty_pdf,
    parse_mcq_questions,
    extract_answer_key,
)

from .services.question_classifier import classify_extracted_question


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def is_admin_user(user):
    return user.is_staff or getattr(user, "role", None) == "admin"


def is_student_user(user):
    return getattr(user, "role", None) == "student"


import random

from .models import Question, MockExamQuestion, AttemptDetail


def select_questions_for_domain(user, domain, count):
    """
    Flexible question selection for one domain.

    Priority:
    1. Unused/unseen questions
    2. Previously wrong questions
    3. Any remaining questions if needed

    This prevents hard errors when unused questions are not enough.
    """

    all_questions = Question.objects.filter(
        topic__domain=domain,
        is_active=True
    ).select_related(
        "topic",
        "topic__domain"
    ).prefetch_related("choices")

    available_count = all_questions.count()

    if available_count < count:
        raise ValueError(
            f"Not enough questions in domain '{domain.name}'. "
            f"Available: {available_count}, required: {count}."
        )

    attempted_question_ids = AttemptDetail.objects.filter(
        attempt__student=user,
        question__topic__domain=domain
    ).values_list("question_id", flat=True).distinct()

    wrong_question_ids = AttemptDetail.objects.filter(
        attempt__student=user,
        question__topic__domain=domain,
        is_correct=False
    ).values_list("question_id", flat=True).distinct()

    selected_questions = []
    selected_ids = set()

    # 1. Prefer unseen questions
    unseen_questions = list(
        all_questions.exclude(id__in=attempted_question_ids)
    )

    random.shuffle(unseen_questions)

    for question in unseen_questions:
        if len(selected_questions) >= count:
            break

        selected_questions.append(question)
        selected_ids.add(question.id)

    # 2. If not enough, add previously wrong questions
    if len(selected_questions) < count:
        wrong_questions = list(
            all_questions.filter(id__in=wrong_question_ids)
            .exclude(id__in=selected_ids)
        )

        random.shuffle(wrong_questions)

        for question in wrong_questions:
            if len(selected_questions) >= count:
                break

            selected_questions.append(question)
            selected_ids.add(question.id)

    # 3. If still not enough, fill with any remaining questions
    if len(selected_questions) < count:
        remaining_questions = list(
            all_questions.exclude(id__in=selected_ids)
        )

        random.shuffle(remaining_questions)

        for question in remaining_questions:
            if len(selected_questions) >= count:
                break

            selected_questions.append(question)
            selected_ids.add(question.id)

    if len(selected_questions) < count:
        raise ValueError(
            f"Could not select enough questions from domain '{domain.name}'. "
            f"Selected: {len(selected_questions)}, required: {count}."
        )

    return selected_questions


def select_questions_for_course(user, course, total_questions):
    """
    Flexible question selection for whole course mock exam.

    Priority:
    1. Unused/unseen questions
    2. Previously wrong questions
    3. Any remaining questions if needed
    """

    all_questions = Question.objects.filter(
        topic__domain__course=course,
        is_active=True
    ).select_related(
        "topic",
        "topic__domain"
    ).prefetch_related("choices")

    available_count = all_questions.count()

    if available_count < total_questions:
        raise ValueError(
            f"Not enough questions. "
            f"Available: {available_count}, requested: {total_questions}."
        )

    attempted_question_ids = AttemptDetail.objects.filter(
        attempt__student=user,
        question__topic__domain__course=course
    ).values_list("question_id", flat=True).distinct()

    wrong_question_ids = AttemptDetail.objects.filter(
        attempt__student=user,
        question__topic__domain__course=course,
        is_correct=False
    ).values_list("question_id", flat=True).distinct()

    selected_questions = []
    selected_ids = set()

    # 1. Prefer unseen questions
    unseen_questions = list(
        all_questions.exclude(id__in=attempted_question_ids)
    )

    random.shuffle(unseen_questions)

    for question in unseen_questions:
        if len(selected_questions) >= total_questions:
            break

        selected_questions.append(question)
        selected_ids.add(question.id)

    # 2. If not enough, add previously wrong questions
    if len(selected_questions) < total_questions:
        wrong_questions = list(
            all_questions.filter(id__in=wrong_question_ids)
            .exclude(id__in=selected_ids)
        )

        random.shuffle(wrong_questions)

        for question in wrong_questions:
            if len(selected_questions) >= total_questions:
                break

            selected_questions.append(question)
            selected_ids.add(question.id)

    # 3. If still not enough, fill with any remaining questions
    if len(selected_questions) < total_questions:
        remaining_questions = list(
            all_questions.exclude(id__in=selected_ids)
        )

        random.shuffle(remaining_questions)

        for question in remaining_questions:
            if len(selected_questions) >= total_questions:
                break

            selected_questions.append(question)
            selected_ids.add(question.id)

    if len(selected_questions) < total_questions:
        raise ValueError(
            f"Could not select enough questions. "
            f"Selected: {len(selected_questions)}, required: {total_questions}."
        )

    return selected_questions

def rank_questions_for_student(user, queryset):
    """
    Rank questions by priority:

    1. Questions never used in a previous mock exam
    2. Previously answered incorrectly
    3. Any other previously used questions
    """

    questions = list(
        queryset.select_related(
            "topic",
            "topic__domain",
            "topic__domain__course"
        ).prefetch_related("choices")
    )

    if not questions:
        return []

    question_ids = [question.id for question in questions]

    used_question_ids = set(
        MockExamQuestion.objects.filter(
            mock_exam__student=user,
            question_id__in=question_ids
        ).values_list("question_id", flat=True)
    )

    wrong_question_ids = set(
        AttemptDetail.objects.filter(
            attempt__student=user,
            question_id__in=question_ids,
            is_correct=False
        ).values_list("question_id", flat=True)
    )

    unseen_questions = [
        question
        for question in questions
        if question.id not in used_question_ids
    ]

    wrong_questions = [
        question
        for question in questions
        if question.id in wrong_question_ids
        and question.id in used_question_ids
    ]

    prioritized_ids = {
        question.id
        for question in unseen_questions + wrong_questions
    }

    remaining_questions = [
        question
        for question in questions
        if question.id not in prioritized_ids
    ]

    random.shuffle(unseen_questions)
    random.shuffle(wrong_questions)
    random.shuffle(remaining_questions)

    return (
        unseen_questions
        + wrong_questions
        + remaining_questions
    )


def select_questions_for_blueprint(user, blueprint):
    """
    Generate an exam using blueprint topic rules.

    Selection process:
    1. Select questions from the exact required topic.
    2. Fill shortages using other questions in the same domain.
    3. Fill remaining shortages using the whole course.
    4. Never duplicate a question inside the same mock exam.

    Returns:
        selected_questions
        allocation_report
        warnings
    """

    topic_rules = list(
        blueprint.topic_rules.select_related(
            "topic",
            "topic__domain",
            "topic__domain__course"
        ).order_by(
            "topic__domain__name",
            "topic__name"
        )
    )

    if not topic_rules:
        raise ValueError(
            "This blueprint has no topic rules."
        )

    topic_rule_total = sum(
        rule.question_count
        for rule in topic_rules
    )

    if topic_rule_total != blueprint.total_questions:
        raise ValueError(
            f"Blueprint total_questions is "
            f"{blueprint.total_questions}, but topic rules "
            f"add up to {topic_rule_total}."
        )

    total_available = Question.objects.filter(
        topic__domain__course=blueprint.course,
        is_active=True
    ).count()

    if total_available < blueprint.total_questions:
        raise ValueError(
            f"Not enough active questions for this blueprint. "
            f"Available: {total_available}, "
            f"required: {blueprint.total_questions}."
        )

    selected_by_rule = {}
    selected_ids = set()
    allocation_report = []
    warnings = []

    # --------------------------------------------------
    # Pass 1: Give every topic its exact available questions
    # before fallback questions are used.
    # --------------------------------------------------

    for rule in topic_rules:
        topic_queryset = Question.objects.filter(
            topic=rule.topic,
            is_active=True
        ).exclude(
            id__in=selected_ids
        )

        ranked_questions = rank_questions_for_student(
            user,
            topic_queryset
        )

        exact_questions = ranked_questions[
            :rule.question_count
        ]

        selected_by_rule[rule.id] = list(exact_questions)

        selected_ids.update(
            question.id
            for question in exact_questions
        )

    # --------------------------------------------------
    # Pass 2: Fill topic shortages
    # --------------------------------------------------

    for rule in topic_rules:
        topic = rule.topic
        required = rule.question_count

        selected_for_rule = selected_by_rule[rule.id]

        exact_count = len(selected_for_rule)
        domain_fallback_count = 0
        course_fallback_count = 0

        shortage = required - len(selected_for_rule)

        # Same-domain fallback
        if shortage > 0:
            domain_queryset = Question.objects.filter(
                topic__domain=topic.domain,
                is_active=True
            ).exclude(
                id__in=selected_ids
            )

            domain_candidates = rank_questions_for_student(
                user,
                domain_queryset
            )

            domain_fallback = domain_candidates[:shortage]

            selected_for_rule.extend(domain_fallback)

            selected_ids.update(
                question.id
                for question in domain_fallback
            )

            domain_fallback_count = len(domain_fallback)
            shortage = required - len(selected_for_rule)

        # Whole-course fallback
        if shortage > 0:
            course_queryset = Question.objects.filter(
                topic__domain__course=blueprint.course,
                is_active=True
            ).exclude(
                id__in=selected_ids
            )

            course_candidates = rank_questions_for_student(
                user,
                course_queryset
            )

            course_fallback = course_candidates[:shortage]

            selected_for_rule.extend(course_fallback)

            selected_ids.update(
                question.id
                for question in course_fallback
            )

            course_fallback_count = len(course_fallback)
            shortage = required - len(selected_for_rule)

        if shortage > 0:
            raise ValueError(
                f"Could not allocate enough questions for "
                f"topic '{topic.name}'. "
                f"Required: {required}, "
                f"selected: {len(selected_for_rule)}."
            )

        if domain_fallback_count or course_fallback_count:
            warnings.append(
                {
                    "topic": topic.name,
                    "domain": topic.domain.name,
                    "required": required,
                    "exact_topic_questions": exact_count,
                    "domain_fallback_questions": domain_fallback_count,
                    "course_fallback_questions": course_fallback_count,
                }
            )

        allocation_report.append(
            {
                "domain": topic.domain.name,
                "topic": topic.name,
                "required": required,
                "exact_topic_questions": exact_count,
                "domain_fallback_questions": domain_fallback_count,
                "course_fallback_questions": course_fallback_count,
                "selected_total": len(selected_for_rule),
            }
        )

    selected_questions = []

    for rule in topic_rules:
        selected_questions.extend(
            selected_by_rule[rule.id]
        )

    if len(selected_questions) != blueprint.total_questions:
        raise ValueError(
            f"Blueprint generated {len(selected_questions)} "
            f"questions instead of "
            f"{blueprint.total_questions}."
        )

    random.shuffle(selected_questions)

    return selected_questions, allocation_report, warnings


# --------------------------------------------------
# Basic CRUD ViewSets
# --------------------------------------------------

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAdminOrReadOnly]


class DomainViewSet(viewsets.ModelViewSet):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [IsAdminOrReadOnly]


class TopicViewSet(viewsets.ModelViewSet):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    permission_classes = [IsAdminOrReadOnly]


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAdminOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ChoiceViewSet(viewsets.ModelViewSet):
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer
    permission_classes = [IsAdminOrReadOnly]


class MockExamViewSet(viewsets.ModelViewSet):
    serializer_class = MockExamSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if is_admin_user(user):
            return MockExam.objects.all()

        return MockExam.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class MockExamQuestionViewSet(viewsets.ModelViewSet):
    queryset = MockExamQuestion.objects.all()
    serializer_class = MockExamQuestionSerializer
    permission_classes = [IsAuthenticated]


class ExamAttemptViewSet(viewsets.ModelViewSet):
    serializer_class = ExamAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if is_admin_user(user):
            return ExamAttempt.objects.all()

        return ExamAttempt.objects.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class AttemptDetailViewSet(viewsets.ModelViewSet):
    queryset = AttemptDetail.objects.all()
    serializer_class = AttemptDetailSerializer
    permission_classes = [IsAuthenticated]


# --------------------------------------------------
# Exam Blueprint ViewSets
# --------------------------------------------------

class ExamBlueprintViewSet(viewsets.ModelViewSet):
    serializer_class = ExamBlueprintSerializer
    permission_classes = [IsAdminOrReadOnly]
    def get_queryset(self):
        user = self.request.user

        if is_admin_user(user):
            return ExamBlueprint.objects.all().order_by("-created_at")

        return ExamBlueprint.objects.filter(is_active=True)


class ExamBlueprintDomainRuleViewSet(viewsets.ModelViewSet):
    serializer_class = ExamBlueprintDomainRuleSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user

        if is_admin_user(user):
            return ExamBlueprintDomainRule.objects.all()

        return ExamBlueprintDomainRule.objects.filter(
            blueprint__is_active=True
        )


# --------------------------------------------------
# Generate Mock Exam
# Supports:
# 1. course_id simple mode
# 2. blueprint_id real exit exam mode
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_mock_exam(request):
    user = request.user

    if not is_student_user(user):
        return Response(
            {"detail": "Only students can generate mock exams."},
            status=status.HTTP_403_FORBIDDEN
        )

    blueprint_id = request.data.get("blueprint_id")
    course_id = request.data.get("course_id")

    selected_questions = []
    course = None
    exam_title = "Mock Exam"
    duration_minutes = int(request.data.get("duration_minutes", 30))
    mode = "course"

    allocation_report = []
    warnings = []

    try:
        # Blueprint mode: official-style Exit Exam simulation
        if blueprint_id:
            try:
                blueprint = ExamBlueprint.objects.get(
                    id=blueprint_id,
                    is_active=True
                )
            except ExamBlueprint.DoesNotExist:
                return Response(
                    {"detail": "Active exam blueprint not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            course = blueprint.course
            exam_title = blueprint.title
            duration_minutes = blueprint.duration_minutes
            mode = "blueprint"

            selected_questions, allocation_report, warnings = (
                select_questions_for_blueprint(
                    user=user,
                    blueprint=blueprint
                )
            )

        # Course mode: normal random mock exam
        else:
            if not course_id:
                return Response(
                    {"detail": "course_id or blueprint_id is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                course = Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                return Response(
                    {"detail": "Course not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            total_questions = int(request.data.get("total_questions", 5))

            selected_questions = select_questions_for_course(
                user=user,
                course=course,
                total_questions=total_questions
            )

    except ValueError as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        exam_number = MockExam.objects.filter(
            student=user,
            course=course
        ).count() + 1

        mock_exam = MockExam.objects.create(
            student=user,
            course=course,
            title=f"{exam_title} {exam_number}",
            exam_number=exam_number,
            total_questions=len(selected_questions),
            duration_minutes=duration_minutes,
            status=MockExam.Status.GENERATED
        )

        for index, question in enumerate(selected_questions, start=1):
            MockExamQuestion.objects.create(
                mock_exam=mock_exam,
                question=question,
                order=index
            )

    serializer = MockExamDetailSerializer(mock_exam)

    return Response(
    {
        "message": "Mock exam generated successfully.",
        "mode": mode,
        "blueprint_followed_exactly": (
            mode == "blueprint" and not warnings
        ),
        "fallback_used": bool(warnings),
        "allocation_report": (
            allocation_report
            if mode == "blueprint"
            else []
        ),
        "warnings": warnings,
        "mock_exam": serializer.data
    },
    status=status.HTTP_201_CREATED
)

    


# --------------------------------------------------
# Submit Mock Exam
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_mock_exam(request):
    user = request.user

    mock_exam_id = request.data.get("mock_exam_id")
    answers = request.data.get("answers", [])
    duration_seconds = int(request.data.get("duration_seconds", 0))

    if not mock_exam_id:
        return Response(
            {"detail": "mock_exam_id is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        mock_exam = MockExam.objects.get(id=mock_exam_id, student=user)
    except MockExam.DoesNotExist:
        return Response(
            {"detail": "Mock exam not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if hasattr(mock_exam, "attempt"):
        return Response(
            {"detail": "This mock exam has already been submitted."},
            status=status.HTTP_400_BAD_REQUEST
        )

    mock_questions = MockExamQuestion.objects.filter(
        mock_exam=mock_exam
    ).select_related("question").prefetch_related("question__choices")

    total_questions = mock_questions.count()

    if total_questions == 0:
        return Response(
            {"detail": "This mock exam has no questions."},
            status=status.HTTP_400_BAD_REQUEST
        )

    answer_map = {
        int(item["question_id"]): item.get("selected_choice_id")
        for item in answers
        if "question_id" in item
    }

    correct_count = 0
    result_details = []

    with transaction.atomic():
        attempt = ExamAttempt.objects.create(
            mock_exam=mock_exam,
            student=user,
            status=ExamAttempt.Status.SUBMITTED,
            duration_seconds=duration_seconds,
            submitted_at=timezone.now()
        )

        for mock_question in mock_questions:
            question = mock_question.question
            selected_choice_id = answer_map.get(question.id)

            selected_choice = None
            is_correct = False

            if selected_choice_id:
                selected_choice = Choice.objects.filter(
                    id=selected_choice_id,
                    question=question
                ).first()

                if selected_choice:
                    is_correct = selected_choice.is_correct

            if is_correct:
                correct_count += 1

            AttemptDetail.objects.create(
                attempt=attempt,
                question=question,
                selected_choice=selected_choice,
                is_correct=is_correct,
                response_time_seconds=0
            )

            update_topic_performance(
                student=user,
                question=question,
                is_correct=is_correct
            )

            if not is_correct:
                add_wrong_question_to_spaced_repetition(
                    student=user,
                    question=question
                )

            correct_choice = question.choices.filter(is_correct=True).first()

            result_details.append({
                "question_id": question.id,
                "question": question.text,
                "selected_choice_id": selected_choice.id if selected_choice else None,
                "selected_answer": selected_choice.text if selected_choice else None,
                "correct_answer": correct_choice.text if correct_choice else None,
                "is_correct": is_correct,
                "explanation": question.explanation
            })

        score = round((correct_count / total_questions) * 100, 2)

        attempt.total_score = score
        attempt.save()

        mock_exam.status = MockExam.Status.SUBMITTED
        mock_exam.save()

        readiness_obj = calculate_readiness_score(
            student=user,
            course=mock_exam.course
        )

    return Response(
        {
            "message": "Exam submitted successfully.",
            "attempt_id": attempt.id,
            "score": score,
            "readiness_score": readiness_obj.score,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "details": result_details
        },
        status=status.HTTP_200_OK
    )




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_exam_results(request):
    user = request.user

    if not is_student_user(user):
        return Response(
            {"detail": "Only students can view their results."},
            status=status.HTTP_403_FORBIDDEN
        )

    attempts = ExamAttempt.objects.filter(
        student=user
    ).select_related(
        "mock_exam",
        "mock_exam__course"
    ).order_by("-submitted_at")

    results = []

    for attempt in attempts:
        total_questions = attempt.details.count()
        correct_count = attempt.details.filter(is_correct=True).count()

        results.append({
            "attempt_id": attempt.id,
            "mock_exam_id": attempt.mock_exam.id,
            "exam_title": attempt.mock_exam.title,
            "course": attempt.mock_exam.course.name,
            "score": attempt.total_score,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "duration_seconds": attempt.duration_seconds,
            "status": attempt.status,
            "submitted_at": attempt.submitted_at,
        })

    return Response(
        {
            "results": results
        },
        status=status.HTTP_200_OK
    )
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def exam_result_detail(request, attempt_id):
    user = request.user

    if not is_student_user(user):
        return Response(
            {"detail": "Only students can view result details."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        attempt = ExamAttempt.objects.select_related(
            "mock_exam",
            "mock_exam__course"
        ).get(
            id=attempt_id,
            student=user
        )
    except ExamAttempt.DoesNotExist:
        return Response(
            {"detail": "Exam attempt not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    details = AttemptDetail.objects.filter(
        attempt=attempt
    ).select_related(
        "question",
        "question__topic",
        "question__topic__domain",
        "selected_choice"
    ).prefetch_related("question__choices")

    question_details = []

    for detail in details:
        correct_choice = detail.question.choices.filter(
            is_correct=True
        ).first()

        question_details.append({
            "question_id": detail.question.id,
            "question": detail.question.text,
            "topic": detail.question.topic.name,
            "domain": detail.question.topic.domain.name,
            "selected_choice_id": detail.selected_choice.id if detail.selected_choice else None,
            "selected_answer": detail.selected_choice.text if detail.selected_choice else None,
            "correct_choice_id": correct_choice.id if correct_choice else None,
            "correct_answer": correct_choice.text if correct_choice else None,
            "is_correct": detail.is_correct,
            "explanation": detail.question.explanation,
            "response_time_seconds": detail.response_time_seconds
        })

    return Response(
        {
            "attempt_id": attempt.id,
            "mock_exam_id": attempt.mock_exam.id,
            "exam_title": attempt.mock_exam.title,
            "course": attempt.mock_exam.course.name,
            "score": attempt.total_score,
            "duration_seconds": attempt.duration_seconds,
            "submitted_at": attempt.submitted_at,
            "questions": question_details
        },
        status=status.HTTP_200_OK
    )

# --------------------------------------------------
# Exam PDF Importer
# --------------------------------------------------

class ExamPdfImportViewSet(viewsets.ModelViewSet):
    serializer_class = ExamPdfImportSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        user = self.request.user

        if is_admin_user(user):
            return ExamPdfImport.objects.all().order_by("-uploaded_at")

        return ExamPdfImport.objects.none()

    def perform_create(self, serializer):
        if not is_admin_user(self.request.user):
            raise PermissionDenied("Only admin can upload exam PDFs.")

        serializer.save(uploaded_by=self.request.user)


class ExtractedQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = ExtractedQuestionSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        user = self.request.user

        if is_admin_user(user):
            return ExtractedQuestion.objects.all().order_by("-created_at")

        return ExtractedQuestion.objects.none()

    def perform_create(self, serializer):
        if not is_admin_user(self.request.user):
            raise PermissionDenied("Only admin can create extracted questions.")

        serializer.save()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def process_exam_pdf_import(request, import_id):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only admin can process exam PDFs."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        exam_import = ExamPdfImport.objects.get(id=import_id)
    except ExamPdfImport.DoesNotExist:
        return Response(
            {"detail": "Exam PDF import not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    approved_count = exam_import.extracted_questions.filter(
        status=ExtractedQuestion.Status.APPROVED
    ).count()

    if approved_count > 0:
        return Response(
            {
                "detail": (
                    "This PDF import already contains approved questions "
                    "and cannot be processed again."
                ),
                "approved_questions": approved_count,
                "current_status": exam_import.status,
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Continue with your existing PDF processing code here
    exam_import.status = ExamPdfImport.Status.PROCESSING
    exam_import.error_message = ""
    exam_import.save()
    

    exam_import.status = ExamPdfImport.Status.PROCESSING
    exam_import.error_message = ""
    exam_import.save()

    try:
        extracted_text = extract_text_from_pdf(exam_import.file.path)

        if is_scanned_or_empty_pdf(extracted_text):
            exam_import.status = ExamPdfImport.Status.FAILED
            exam_import.extracted_text = extracted_text
            exam_import.error_message = (
                "This PDF appears to be scanned or empty. OCR is not supported yet."
            )
            exam_import.save()

            return Response(
                {
                    "detail": "PDF processing failed.",
                    "error": exam_import.error_message
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        parsed_questions = parse_mcq_questions(extracted_text)
        answer_key = extract_answer_key(extracted_text)

        if len(parsed_questions) == 0:
            exam_import.status = ExamPdfImport.Status.FAILED
            exam_import.extracted_text = extracted_text
            exam_import.error_message = (
                "No MCQ questions detected. Please check the PDF format."
            )
            exam_import.save()

            return Response(
                {
                    "detail": "No questions detected.",
                    "text_preview": extracted_text[:1000]
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        ExtractedQuestion.objects.filter(
            exam_import=exam_import,
            status=ExtractedQuestion.Status.DRAFT
        ).delete()

        for item in parsed_questions:
            q_number = item.get("question_number")

            ExtractedQuestion.objects.create(
                exam_import=exam_import,
                question_number=q_number,
                question_text=item.get("question_text", ""),
                option_a=item.get("option_a", ""),
                option_b=item.get("option_b", ""),
                option_c=item.get("option_c", ""),
                option_d=item.get("option_d", ""),
                correct_answer=item.get("correct_answer") or answer_key.get(q_number, ""),
                explanation=item.get("explanation", "")
            )

        exam_import.status = ExamPdfImport.Status.NEEDS_REVIEW
        exam_import.extracted_text = extracted_text
        exam_import.error_message = ""
        exam_import.save()

        return Response(
            {
                "message": "PDF processed successfully.",
                "detected_questions": len(parsed_questions),
                "status": exam_import.status
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        exam_import.status = ExamPdfImport.Status.FAILED
        exam_import.error_message = str(e)
        exam_import.save()

        return Response(
            {
                "detail": "PDF processing failed.",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve_extracted_question(request, extracted_question_id):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only admin can approve extracted questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        extracted = ExtractedQuestion.objects.get(id=extracted_question_id)
    except ExtractedQuestion.DoesNotExist:
        return Response(
            {"detail": "Extracted question not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if extracted.status == ExtractedQuestion.Status.APPROVED:
        return Response(
            {"detail": "This question is already approved."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not extracted.topic:
        return Response(
            {"detail": "Topic is required before approval."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if extracted.correct_answer not in ["A", "B", "C", "D"]:
        return Response(
            {"detail": "Correct answer must be A, B, C, or D before approval."},
            status=status.HTTP_400_BAD_REQUEST
        )

    options = {
        "A": extracted.option_a,
        "B": extracted.option_b,
        "C": extracted.option_c,
        "D": extracted.option_d,
    }

    if not all(options.values()):
        return Response(
            {"detail": "All four options are required before approval."},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        question = Question.objects.create(
            topic=extracted.topic,
            text=extracted.question_text,
            bloom_level=extracted.bloom_level,
            difficulty=extracted.difficulty,
            explanation=extracted.explanation,
            created_by=user,
            is_active=True
        )

        for letter, option_text in options.items():
            Choice.objects.create(
                question=question,
                text=option_text,
                is_correct=(letter == extracted.correct_answer)
            )

        extracted.status = ExtractedQuestion.Status.APPROVED
        extracted.approved_question = question
        extracted.save()

    return Response(
        {
            "message": "Extracted question approved and added to question bank.",
            "question_id": question.id
        },
        status=status.HTTP_201_CREATED
    )
def extracted_question_is_ready(extracted):
    return (
        extracted.question_text
        and extracted.option_a
        and extracted.option_b
        and extracted.option_c
        and extracted.option_d
        and extracted.correct_answer in ["A", "B", "C", "D"]
        and extracted.topic is not None
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_approve_extracted_questions(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only admin can bulk approve extracted questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    ids = request.data.get("ids", [])
    import_id = request.data.get("import_id")

    queryset = ExtractedQuestion.objects.filter(
        status=ExtractedQuestion.Status.DRAFT
    ).select_related("topic", "domain")

    if ids:
        queryset = queryset.filter(id__in=ids)

    if import_id:
        queryset = queryset.filter(exam_import_id=import_id)

    approved = []
    skipped = []

    with transaction.atomic():
        for extracted in queryset:
            if not extracted_question_is_ready(extracted):
                reasons = []

                if not extracted.topic:
                    reasons.append("missing_topic")

                if extracted.correct_answer not in ["A", "B", "C", "D"]:
                    reasons.append("missing_or_invalid_correct_answer")

                if not all([
                    extracted.option_a,
                    extracted.option_b,
                    extracted.option_c,
                    extracted.option_d,
                ]):
                    reasons.append("missing_options")

                if not extracted.question_text:
                    reasons.append("missing_question_text")

                skipped.append({
                    "id": extracted.id,
                    "question_number": extracted.question_number,
                    "reasons": reasons,
                })

                continue

            question = Question.objects.create(
                topic=extracted.topic,
                text=extracted.question_text,
                bloom_level=extracted.bloom_level,
                difficulty=extracted.difficulty,
                explanation=extracted.explanation,
                created_by=user,
                is_active=True
            )

            options = {
                "A": extracted.option_a,
                "B": extracted.option_b,
                "C": extracted.option_c,
                "D": extracted.option_d,
            }

            for letter, option_text in options.items():
                Choice.objects.create(
                    question=question,
                    text=option_text,
                    is_correct=(letter == extracted.correct_answer)
                )

            extracted.status = ExtractedQuestion.Status.APPROVED
            extracted.approved_question = question
            extracted.save()

            approved.append({
                "extracted_question_id": extracted.id,
                "question_number": extracted.question_number,
                "question_id": question.id,
            })

    return Response(
        {
            "message": "Bulk approval completed.",
            "approved_count": len(approved),
            "skipped_count": len(skipped),
            "approved": approved,
            "skipped": skipped,
        },
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_extracted_question(request, extracted_question_id):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only admin can reject extracted questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        extracted = ExtractedQuestion.objects.get(id=extracted_question_id)
    except ExtractedQuestion.DoesNotExist:
        return Response(
            {"detail": "Extracted question not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if extracted.status == ExtractedQuestion.Status.APPROVED:
        return Response(
            {"detail": "Approved questions cannot be rejected."},
            status=status.HTTP_400_BAD_REQUEST
        )

    extracted.status = ExtractedQuestion.Status.REJECTED
    extracted.save()

    return Response(
        {
            "message": "Extracted question rejected successfully.",
            "extracted_question_id": extracted.id,
            "status": extracted.status
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_dashboard_stats(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only admin can view dashboard statistics."},
            status=status.HTTP_403_FORBIDDEN
        )

    User = get_user_model()

    total_students = User.objects.filter(role="student").count()
    total_admins = User.objects.filter(role="admin").count()

    total_courses = Course.objects.count()
    total_domains = Domain.objects.count()
    total_topics = Topic.objects.count()

    total_questions = Question.objects.count()
    active_questions = Question.objects.filter(is_active=True).count()

    total_mock_exams = MockExam.objects.count()
    total_attempts = ExamAttempt.objects.count()

    submitted_attempts = ExamAttempt.objects.filter(
        status=ExamAttempt.Status.SUBMITTED
    ).count()

    average_readiness = ReadinessScore.objects.aggregate(
        avg_score=Avg("score")
    )["avg_score"]

    average_exam_score = ExamAttempt.objects.aggregate(
        avg_score=Avg("total_score")
    )["avg_score"]

    pdf_import_stats = {
        "total": ExamPdfImport.objects.count(),
        "uploaded": ExamPdfImport.objects.filter(
            status=ExamPdfImport.Status.UPLOADED
        ).count(),
        "needs_review": ExamPdfImport.objects.filter(
            status=ExamPdfImport.Status.NEEDS_REVIEW
        ).count(),
        "approved": ExamPdfImport.objects.filter(
            status=ExamPdfImport.Status.APPROVED
        ).count(),
        "failed": ExamPdfImport.objects.filter(
            status=ExamPdfImport.Status.FAILED
        ).count(),
    }

    extracted_question_stats = {
        "total": ExtractedQuestion.objects.count(),
        "draft": ExtractedQuestion.objects.filter(
            status=ExtractedQuestion.Status.DRAFT
        ).count(),
        "approved": ExtractedQuestion.objects.filter(
            status=ExtractedQuestion.Status.APPROVED
        ).count(),
        "rejected": ExtractedQuestion.objects.filter(
            status=ExtractedQuestion.Status.REJECTED
        ).count(),
    }

    question_distribution_by_domain = Question.objects.values(
        "topic__domain__id",
        "topic__domain__name"
    ).annotate(
        total=Count("id")
    ).order_by("-total")

    performances = StudentTopicPerformance.objects.filter(
        total_attempts__gt=0
    ).select_related(
        "student",
        "domain",
        "topic"
    )

    weakest_topics = sorted(
        performances,
        key=lambda item: item.accuracy
    )[:5]

    recent_attempts = ExamAttempt.objects.select_related(
        "student",
        "mock_exam",
        "mock_exam__course"
    ).order_by("-submitted_at")[:10]

    return Response(
        {
            "users": {
                "total_students": total_students,
                "total_admins": total_admins,
            },

            "academic_structure": {
                "total_courses": total_courses,
                "total_domains": total_domains,
                "total_topics": total_topics,
            },

            "question_bank": {
                "total_questions": total_questions,
                "active_questions": active_questions,
                "distribution_by_domain": [
                    {
                        "domain_id": item["topic__domain__id"],
                        "domain": item["topic__domain__name"],
                        "total_questions": item["total"],
                    }
                    for item in question_distribution_by_domain
                ],
            },

            "exams": {
                "total_mock_exams": total_mock_exams,
                "total_attempts": total_attempts,
                "submitted_attempts": submitted_attempts,
                "average_exam_score": round(float(average_exam_score), 2)
                if average_exam_score is not None else 0,
            },

            "readiness": {
                "average_readiness_score": round(float(average_readiness), 2)
                if average_readiness is not None else 0,
            },

            "pdf_imports": pdf_import_stats,

            "extracted_questions": extracted_question_stats,

            "weakest_topics": [
                {
                    "student": item.student.username,
                    "domain": item.domain.name,
                    "topic": item.topic.name,
                    "accuracy": item.accuracy,
                    "correct_attempts": item.correct_attempts,
                    "total_attempts": item.total_attempts,
                }
                for item in weakest_topics
            ],

            "recent_attempts": [
                {
                    "attempt_id": attempt.id,
                    "student": attempt.student.username,
                    "exam_title": attempt.mock_exam.title,
                    "course": attempt.mock_exam.course.name,
                    "score": attempt.total_score,
                    "status": attempt.status,
                    "submitted_at": attempt.submitted_at,
                }
                for attempt in recent_attempts
            ],
        },
        status=status.HTTP_200_OK
    )
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auto_classify_extracted_questions(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only admin can auto-classify extracted questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    import_id = request.data.get("import_id")

    queryset = ExtractedQuestion.objects.filter(
        status=ExtractedQuestion.Status.DRAFT
    ).select_related("exam_import", "exam_import__course")

    if import_id:
        queryset = queryset.filter(exam_import_id=import_id)

    updated = 0
    not_matched = 0
    results = []

    for extracted in queryset:
        classification = classify_extracted_question(extracted)
        topic = classification["topic"]

        if topic:
            extracted.topic = topic
            extracted.domain = topic.domain
            extracted.bloom_level = classification["bloom_level"]

            extracted.save(
                 update_fields=[
                        "topic",
                        "domain",
                        "bloom_level",
                    ]
    )

            updated += 1

            results.append({
                "id": extracted.id,
                "question_number": extracted.question_number,
                "matched_topic": topic.name,
                "matched_domain": topic.domain.name,
                "score": classification["score"],
            })
        else:
            not_matched += 1

            results.append({
                "id": extracted.id,
                "question_number": extracted.question_number,
                "matched_topic": None,
                "matched_domain": None,
                "score": classification["score"],
                "suggested_topic_name": classification["matched_topic_name"],
            })

    return Response(
        {
            "message": "Auto-classification completed.",
            "updated": updated,
            "not_matched": not_matched,
            "results": results,
        },
        status=status.HTTP_200_OK
    )
def extracted_question_is_ready(extracted):
    return (
        extracted.question_text
        and extracted.option_a
        and extracted.option_b
        and extracted.option_c
        and extracted.option_d
        and extracted.correct_answer in ["A", "B", "C", "D"]
        and extracted.topic is not None
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_approve_extracted_questions(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only admin can bulk approve extracted questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    import_id = request.data.get("import_id")
    ids = request.data.get("ids", [])
    auto_classify = request.data.get("auto_classify", True)

    queryset = ExtractedQuestion.objects.filter(
        status=ExtractedQuestion.Status.DRAFT
    ).select_related(
        "topic",
        "domain",
        "exam_import",
        "exam_import__course"
    )

    if import_id:
        queryset = queryset.filter(exam_import_id=import_id)

    if ids:
        queryset = queryset.filter(id__in=ids)

    approved_count = 0
    skipped_count = 0
    approved = []
    skipped = []

    with transaction.atomic():
        for extracted in queryset:
            if auto_classify and not extracted.topic:
                classification = classify_extracted_question(extracted)

                if classification["topic"]:
                    extracted.topic = classification["topic"]
                    extracted.domain = classification["topic"].domain
                    extracted.bloom_level = classification["bloom_level"]

                    extracted.save(
                        update_fields=[
                            "topic",
                            "domain",
                            "bloom_level",
                        ]
                    )
                    

            if not extracted_question_is_ready(extracted):
                skipped_count += 1

                reasons = []

                if not extracted.topic:
                    reasons.append("missing_topic")

                if extracted.correct_answer not in ["A", "B", "C", "D"]:
                    reasons.append("missing_or_invalid_correct_answer")

                if not all([
                    extracted.option_a,
                    extracted.option_b,
                    extracted.option_c,
                    extracted.option_d,
                ]):
                    reasons.append("missing_options")

                if not extracted.question_text:
                    reasons.append("missing_question_text")

                skipped.append({
                    "id": extracted.id,
                    "question_number": extracted.question_number,
                    "reasons": reasons,
                })

                continue

            question = Question.objects.create(
                topic=extracted.topic,
                text=extracted.question_text,
                bloom_level=extracted.bloom_level,
                difficulty=extracted.difficulty,
                explanation=extracted.explanation,
                created_by=user,
                is_active=True
            )

            options = {
                "A": extracted.option_a,
                "B": extracted.option_b,
                "C": extracted.option_c,
                "D": extracted.option_d,
            }

            for letter, option_text in options.items():
                Choice.objects.create(
                    question=question,
                    text=option_text,
                    is_correct=(letter == extracted.correct_answer)
                )

            extracted.status = ExtractedQuestion.Status.APPROVED
            extracted.approved_question = question
            extracted.save()

            approved_count += 1

            approved.append({
                "extracted_question_id": extracted.id,
                "question_number": extracted.question_number,
                "question_id": question.id,
            })

    return Response(
        {
            "message": "Bulk approval completed.",
            "approved_count": approved_count,
            "skipped_count": skipped_count,
            "approved": approved,
            "skipped": skipped,
        },
        status=status.HTTP_200_OK
    )
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def question_availability_by_domain(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    course_id = request.query_params.get("course_id")

    domains = Domain.objects.all()

    if course_id:
        domains = domains.filter(course_id=course_id)

    data = []

    for domain in domains:
        total_questions = Question.objects.filter(
            topic__domain=domain,
            is_active=True
        ).count()

        data.append({
            "domain_id": domain.id,
            "domain": domain.name,
            "course_id": domain.course.id,
            "course": domain.course.name,
            "available_questions": total_questions
        })

    return Response(
        {
            "availability": data
        },
        status=status.HTTP_200_OK
    )