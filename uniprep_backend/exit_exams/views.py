from .permissions import IsAdminRole, IsAdminOrReadOnly, IsDepartmentHeadOrSystemAdmin, IsSystemAdminOnly
import random

from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q
from analytics.models import ReadinessScore, StudentTopicPerformance

from .models import (
    Department,
    Course,
    TeacherCourseAssignment,
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
    AuditLog,
    SystemSettings,
)

from .serializers import (
    DepartmentSerializer,
    CourseSerializer,
    TeacherCourseAssignmentSerializer,
    DomainSerializer,
    TopicSerializer,
    QuestionSerializer,
    RejectQuestionSerializer,
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
    AuditLogSerializer,
    DuplicateCheckSerializer,
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
from .services.duplicate_detector import find_duplicates
from .services.audit_logger import (
    log_action,
    snapshot_question,
    snapshot_blueprint,
    snapshot_assignment,
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def is_admin_user(user):
    return user.is_staff or getattr(user, "role", None) in {
        "department_head",
        "system_admin",
        "admin",
    }


def is_student_user(user):
    return getattr(user, "role", None) == "student"


def is_teacher_user(user):
    return getattr(user, "role", None) == "teacher"


def is_department_head_user(user):
    return getattr(user, "role", None) in {"department_head", "admin"}


def is_system_admin_user(user):
    return getattr(user, "role", None) == "system_admin"


def get_user_department(user):
    return getattr(user, "department", None)


def can_review_topic(user, topic):
    if not is_department_head_user(user):
        return False

    department = get_user_department(user)
    if not department or not topic:
        return False

    topic_department_id = topic.domain.course.department_id
    return topic_department_id == department.id


def can_review_question(user, question):
    return can_review_topic(user, question.topic)


def teacher_is_assigned_to_course(user, course_id):
    return TeacherCourseAssignment.objects.filter(
        teacher=user,
        course_id=course_id
    ).exists()


def topic_course_id(topic):
    if not topic:
        return None
    return topic.domain.course_id


def teacher_can_use_topic(user, topic):
    return is_teacher_user(user) and teacher_is_assigned_to_course(
        user,
        topic_course_id(topic)
    )


def department_head_can_manage_course(user, course):
    if is_system_admin_user(user):
        return True
    if is_department_head_user(user):
        department = get_user_department(user)
        return department is not None and course is not None and course.department_id == department.id
    if user.is_staff:
        return True
    return False


def department_head_can_manage_topic(user, topic):
    return department_head_can_manage_course(user, topic.domain.course)


def save_question_choices(question, choices):
    if choices is None:
        return

    question.choices.all().delete()
    Choice.objects.bulk_create([
        Choice(
            question=question,
            text=choice["text"],
            is_correct=choice.get("is_correct", False),
        )
        for choice in choices
    ])


def duplicate_response_for_question(question):
    duplicates = find_duplicates(
        text=question.text,
        course_id=topic_course_id(question.topic),
        threshold=0.85,
        exclude_question_id=question.id,
    )
    if not duplicates:
        return None

    return Response(
        {
            "detail": "Potential duplicate questions found. Choose how to proceed.",
            "code": "duplicate_decision_required",
            "duplicates": duplicates,
        },
        status=status.HTTP_409_CONFLICT,
    )


def resolve_duplicate_decision(request, question):
    action = request.data.get("duplicate_action")
    duplicate_question_id = request.data.get("duplicate_question_id")

    duplicates = find_duplicates(
        text=question.text,
        course_id=topic_course_id(question.topic),
        threshold=0.85,
        exclude_question_id=question.id,
    )
    if not duplicates:
        return None

    duplicate_ids = {item["question_id"] for item in duplicates}

    if not action:
        return duplicate_response_for_question(question)

    if action == "skip":
        return Response(
            {
                "message": "Approval skipped because the question is a duplicate.",
                "skipped": True,
                "duplicates": duplicates,
            },
            status=status.HTTP_200_OK,
        )

    if action == "import_as_new":
        return None

    if action == "replace_existing":
        if not duplicate_question_id or int(duplicate_question_id) not in duplicate_ids:
            return Response(
                {"detail": "A valid duplicate_question_id is required to replace existing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Question.objects.filter(id=duplicate_question_id).update(
            status=Question.Status.ARCHIVED,
            is_active=False,
        )
        return None

    return Response(
        {"detail": "Invalid duplicate_action."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def mark_question_approved(question, user):
    now = timezone.now()
    question.status = Question.Status.APPROVED
    question.reviewed_by = user
    question.approved_by = user
    question.reviewed_at = now
    question.approved_at = now
    question.rejection_reason = ""
    question.is_active = True
    question.save(
        update_fields=[
            "status",
            "reviewed_by",
            "approved_by",
            "reviewed_at",
            "approved_at",
            "rejection_reason",
            "is_active",
        ]
    )


def user_can_access_import(user, exam_import):
    if is_system_admin_user(user) or user.is_staff:
        return True

    if is_teacher_user(user):
        return (
            exam_import.uploaded_by_id == user.id
            and teacher_is_assigned_to_course(user, exam_import.course_id)
        )

    if is_department_head_user(user):
        department = get_user_department(user)
        return (
            department is not None
            and exam_import.course.department_id == department.id
        )

    return False


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
        is_active=True,
        status=Question.Status.APPROVED
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
        is_active=True,
        status=Question.Status.APPROVED
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

    domain_rules = list(
        blueprint.domain_rules.select_related("domain").order_by("domain__name")
    )

    if not topic_rules and not domain_rules:
        raise ValueError(
            "This blueprint has no domain or topic rules."
        )

    if not topic_rules and domain_rules:
        domain_rule_total = sum(r.number_of_questions for r in domain_rules)
        if domain_rule_total != blueprint.total_questions:
            raise ValueError(
                f"Blueprint total_questions is {blueprint.total_questions}, but domain rules add up to {domain_rule_total}."
            )

        selected_ids = set()
        selected_questions = []
        allocation_report = []
        warnings = []

        for rule in domain_rules:
            domain_qs = Question.objects.filter(
                topic__domain=rule.domain,
                is_active=True,
                status=Question.Status.APPROVED
            ).exclude(id__in=selected_ids)

            ranked = rank_questions_for_student(user, domain_qs)
            chosen = list(ranked[:rule.number_of_questions])
            selected_questions.extend(chosen)
            selected_ids.update(q.id for q in chosen)

            if len(chosen) < rule.number_of_questions:
                shortage = rule.number_of_questions - len(chosen)
                warnings.append({
                    "domain": rule.domain.name,
                    "required": rule.number_of_questions,
                    "allocated": len(chosen),
                    "shortage": shortage
                })

            allocation_report.append({
                "domain": rule.domain.name,
                "required": rule.number_of_questions,
                "selected_total": len(chosen)
            })

        if len(selected_questions) < blueprint.total_questions:
            remaining_needed = blueprint.total_questions - len(selected_questions)
            course_qs = Question.objects.filter(
                topic__domain__course=blueprint.course,
                is_active=True,
                status=Question.Status.APPROVED
            ).exclude(id__in=selected_ids)

            fallback = list(rank_questions_for_student(user, course_qs)[:remaining_needed])
            selected_questions.extend(fallback)

        if len(selected_questions) < blueprint.total_questions:
            raise ValueError(
                f"Not enough questions available to fulfill blueprint. Generated {len(selected_questions)} of {blueprint.total_questions}."
            )

        random.shuffle(selected_questions)
        return selected_questions, allocation_report, warnings

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
        is_active=True,
        status=Question.Status.APPROVED
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
            is_active=True,
            status=Question.Status.APPROVED
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
                is_active=True,
                status=Question.Status.APPROVED
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
                is_active=True,
                status=Question.Status.APPROVED
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

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsDepartmentHeadOrSystemAdmin]

    def get_queryset(self):
        user = self.request.user
        base_qs = Department.objects.annotate(course_count=Count("courses"))
        if is_system_admin_user(user):
            return base_qs
        if is_department_head_user(user):
            department = get_user_department(user)
            return base_qs.filter(id=department.id) if department else Department.objects.none()
        if user.is_staff:
            return base_qs
        return Department.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not (is_system_admin_user(user) or (user.is_staff and not is_department_head_user(user))):
            raise PermissionDenied("Only system admins can create departments.")
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        if is_department_head_user(user) and not is_system_admin_user(user):
            department = get_user_department(user)
            if not department or instance.id != department.id:
                raise PermissionDenied("Department heads can update only their own department.")
        elif not (is_system_admin_user(user) or user.is_staff):
            raise PermissionDenied("Only system admins can update departments.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not (is_system_admin_user(user) or (user.is_staff and not is_department_head_user(user))):
            raise PermissionDenied("Only system admins can delete departments.")
        instance.delete()


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = Course.objects.select_related("department")

        if is_system_admin_user(user):
            return queryset

        # Department heads see only their department's courses
        if is_department_head_user(user):
            department = get_user_department(user)
            if department:
                return queryset.filter(department=department)
            return queryset.none()

        # Teachers see only their assigned courses
        if is_teacher_user(user):
            assigned_course_ids = TeacherCourseAssignment.objects.filter(
                teacher=user
            ).values_list("course_id", flat=True)
            return queryset.filter(id__in=assigned_course_ids)

        if user.is_staff:
            return queryset

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        department = serializer.validated_data.get("department") or get_user_department(user)

        if is_department_head_user(user) and not is_system_admin_user(user):
            user_department = get_user_department(user)
            if not user_department:
                raise PermissionDenied("Department head has no department assigned.")
            if department and department.id != user_department.id:
                raise PermissionDenied("Department heads can create courses only in their department.")
            serializer.save(department=user_department)
            return

        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        target_department = serializer.validated_data.get("department", instance.department)

        if is_department_head_user(user) and not is_system_admin_user(user):
            user_department = get_user_department(user)
            if (
                not user_department
                or instance.department_id != user_department.id
                or (target_department and target_department.id != user_department.id)
            ):
                raise PermissionDenied("Department heads can update only their department's courses.")

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if is_department_head_user(user) and not is_system_admin_user(user):
            department = get_user_department(user)
            if not department or instance.department_id != department.id:
                raise PermissionDenied("Department heads can delete only their department's courses.")
        instance.delete()


class TeacherCourseAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherCourseAssignmentSerializer
    permission_classes = [IsDepartmentHeadOrSystemAdmin]

    def get_queryset(self):
        queryset = TeacherCourseAssignment.objects.select_related(
            "teacher",
            "course",
            "course__department"
        )

        teacher_id = self.request.query_params.get("teacher_id")
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)

        user = self.request.user
        if is_system_admin_user(user):
            return queryset

        if is_department_head_user(user):
            department = get_user_department(user)
            return queryset.filter(course__department=department) if department else queryset.none()

        if user.is_staff:
            return queryset

        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        course = serializer.validated_data["course"]
        teacher = serializer.validated_data["teacher"]

        if is_department_head_user(user) and not is_system_admin_user(user):
            department = get_user_department(user)
            if not department or course.department_id != department.id:
                raise PermissionDenied("Department heads can assign teachers only within their department.")
            if teacher.department_id and teacher.department_id != department.id:
                raise PermissionDenied("Department heads can assign only teachers in their department.")

        assignment = serializer.save()
        log_action(
            user=user,
            action=AuditLog.Action.ASSIGNMENT_CHANGED,
            entity_type="assignment",
            entity_id=assignment.id,
            new_value=snapshot_assignment(assignment),
            description=(
                f"{user.username} assigned teacher "
                f"{assignment.teacher.username} to {assignment.course.name}."
            ),
        )

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        course = serializer.validated_data.get("course", instance.course)
        teacher = serializer.validated_data.get("teacher", instance.teacher)

        if is_department_head_user(user) and not is_system_admin_user(user):
            department = get_user_department(user)
            if not department or instance.course.department_id != department.id or course.department_id != department.id:
                raise PermissionDenied("Department heads can update only assignments in their department.")
            if teacher.department_id and teacher.department_id != department.id:
                raise PermissionDenied("Department heads can assign only teachers in their department.")

        assignment = serializer.save()
        log_action(
            user=user,
            action=AuditLog.Action.ASSIGNMENT_CHANGED,
            entity_type="assignment",
            entity_id=assignment.id,
            previous_value=snapshot_assignment(instance),
            new_value=snapshot_assignment(assignment),
            description=(
                f"{user.username} updated assignment "
                f"for teacher {assignment.teacher.username} and course {assignment.course.name}."
            ),
        )

    def perform_destroy(self, instance):
        user = self.request.user
        if is_department_head_user(user) and not is_system_admin_user(user):
            department = get_user_department(user)
            if not department or instance.course.department_id != department.id:
                raise PermissionDenied("Department heads can remove only assignments in their department.")

        prev = snapshot_assignment(instance)
        log_action(
            user=user,
            action=AuditLog.Action.ASSIGNMENT_CHANGED,
            entity_type="assignment",
            entity_id=instance.id,
            previous_value=prev,
            description=(
                f"{user.username} removed teacher "
                f"{instance.teacher.username} from {instance.course.name}."
            ),
        )
        instance.delete()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_assigned_courses(request):
    user = request.user

    if not is_teacher_user(user):
        return Response(
            {"detail": "Only teachers can list assigned courses."},
            status=status.HTTP_403_FORBIDDEN
        )

    assignments = TeacherCourseAssignment.objects.filter(
        teacher=user
    ).select_related(
        "teacher",
        "course",
        "course__department"
    )

    serializer = TeacherCourseAssignmentSerializer(assignments, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


class DomainViewSet(viewsets.ModelViewSet):
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = Domain.objects.select_related("course")

        if is_system_admin_user(user):
            return queryset

        # Department heads see only domains from their department's courses
        if is_department_head_user(user):
            department = get_user_department(user)
            if department:
                return queryset.filter(course__department=department)
            return queryset.none()

        # Teachers see only domains from their assigned courses
        if is_teacher_user(user):
            assigned_course_ids = TeacherCourseAssignment.objects.filter(
                teacher=user
            ).values_list("course_id", flat=True)
            return queryset.filter(course_id__in=assigned_course_ids)

        if user.is_staff:
            return queryset

        return queryset

    def perform_create(self, serializer):
        course = serializer.validated_data["course"]
        if is_department_head_user(self.request.user) and not is_system_admin_user(self.request.user):
            if not department_head_can_manage_course(self.request.user, course):
                raise PermissionDenied("Department heads can create domains only in their department.")
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        course = serializer.validated_data.get("course", instance.course)
        if is_department_head_user(self.request.user) and not is_system_admin_user(self.request.user):
            if (
                not department_head_can_manage_course(self.request.user, instance.course)
                or not department_head_can_manage_course(self.request.user, course)
            ):
                raise PermissionDenied("Department heads can update only their department's domains.")
        serializer.save()

    def perform_destroy(self, instance):
        if is_department_head_user(self.request.user) and not is_system_admin_user(self.request.user):
            if not department_head_can_manage_course(self.request.user, instance.course):
                raise PermissionDenied("Department heads can delete only their department's domains.")
        instance.delete()


class TopicViewSet(viewsets.ModelViewSet):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = Topic.objects.select_related(
            "domain",
            "domain__course",
            "domain__course__department"
        )

        if is_system_admin_user(user):
            return queryset

        # Department heads see only topics from their department's courses
        if is_department_head_user(user):
            department = get_user_department(user)
            if department:
                return queryset.filter(domain__course__department=department)
            return queryset.none()

        # Teachers see only topics from their assigned courses
        if is_teacher_user(user):
            assigned_course_ids = TeacherCourseAssignment.objects.filter(
                teacher=user
            ).values_list("course_id", flat=True)
            return queryset.filter(domain__course_id__in=assigned_course_ids)

        if user.is_staff:
            return queryset

        return queryset

    def perform_create(self, serializer):
        domain = serializer.validated_data["domain"]
        if is_department_head_user(self.request.user) and not is_system_admin_user(self.request.user):
            if not department_head_can_manage_course(self.request.user, domain.course):
                raise PermissionDenied("Department heads can create topics only in their department.")
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        domain = serializer.validated_data.get("domain", instance.domain)
        if is_department_head_user(self.request.user) and not is_system_admin_user(self.request.user):
            if (
                not department_head_can_manage_course(self.request.user, instance.domain.course)
                or not department_head_can_manage_course(self.request.user, domain.course)
            ):
                raise PermissionDenied("Department heads can update only their department's topics.")
        serializer.save()

    def perform_destroy(self, instance):
        if is_department_head_user(self.request.user) and not is_system_admin_user(self.request.user):
            if not department_head_can_manage_course(self.request.user, instance.domain.course):
                raise PermissionDenied("Department heads can delete only their department's topics.")
        instance.delete()


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Question.objects.select_related(
            "created_by",
            "reviewed_by",
            "topic",
            "topic__domain",
            "topic__domain__course",
            "topic__domain__course__department",
        ).prefetch_related("choices")

        if is_student_user(user):
            return queryset.filter(
                is_active=True,
                status=Question.Status.APPROVED
            )

        if is_teacher_user(user):
            assigned_course_ids = TeacherCourseAssignment.objects.filter(
                teacher=user
            ).values_list("course_id", flat=True)
            return queryset.filter(
                created_by=user,
                topic__domain__course_id__in=assigned_course_ids,
            )

        if is_department_head_user(user):
            department = get_user_department(user)
            if not department:
                return queryset.none()

            return queryset.filter(
                topic__domain__course__department=department
            )

        if is_system_admin_user(user) or user.is_staff:
            return queryset

        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user

        if not is_teacher_user(user):
            raise PermissionDenied("Only teachers can create draft questions.")

        topic = serializer.validated_data["topic"]
        if not teacher_can_use_topic(user, topic):
            raise PermissionDenied("Teachers can create questions only for assigned courses.")

        choices = (
            serializer.validated_data.pop("_validated_choices", None)
            or serializer.validated_data.pop("choice_inputs", None)
        )

        question = serializer.save(
            created_by=user,
            uploaded_by=user,
            source_type=Question.SourceType.MANUAL,
            status=Question.Status.DRAFT,
            is_active=False,
            reviewed_by=None,
            approved_by=None,
            reviewed_at=None,
            approved_at=None,
            rejection_reason="",
            submitted_at=None,
        )
        save_question_choices(question, choices)
        log_action(
            user=user,
            action=AuditLog.Action.CREATED,
            entity_type="question",
            entity_id=question.id,
            new_value=snapshot_question(question),
            description=f"Teacher {user.username} created draft question.",
        )

    def perform_update(self, serializer):
        question = self.get_object()
        user = self.request.user

        editable_statuses = {
            Question.Status.DRAFT,
            Question.Status.REJECTED,
        }

        if not (
            is_teacher_user(user)
            and question.created_by_id == user.id
            and question.status in editable_statuses
        ):
            raise PermissionDenied(
                "Teachers can edit only their own draft or rejected questions."
            )

        prev = snapshot_question(question)
        topic = serializer.validated_data.get("topic", question.topic)
        if not teacher_can_use_topic(user, topic):
            raise PermissionDenied("Teachers can edit questions only for assigned courses.")

        choices = (
            serializer.validated_data.pop("_validated_choices", None)
            or serializer.validated_data.pop("choice_inputs", None)
        )

        updated = serializer.save(
            status=Question.Status.DRAFT,
            is_active=False,
            reviewed_by=None,
            approved_by=None,
            reviewed_at=None,
            approved_at=None,
            rejection_reason="",
            submitted_at=None,
        )
        save_question_choices(updated, choices)
        log_action(
            user=user,
            action=AuditLog.Action.UPDATED,
            entity_type="question",
            entity_id=updated.id,
            previous_value=prev,
            new_value=snapshot_question(updated),
            description=f"Teacher {user.username} edited question (was {prev['status']}).",
        )

    def perform_destroy(self, instance):
        user = self.request.user

        if not (
            is_teacher_user(user)
            and instance.created_by_id == user.id
            and instance.status == Question.Status.DRAFT
        ):
            raise PermissionDenied("Teachers can delete only their own draft questions.")

        log_action(
            user=user,
            action=AuditLog.Action.UPDATED,
            entity_type="question",
            entity_id=instance.id,
            previous_value=snapshot_question(instance),
            description=f"Teacher {user.username} deleted draft question.",
        )
        instance.delete()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_question_for_approval(request, question_id):
    user = request.user

    if not is_teacher_user(user):
        return Response(
            {"detail": "Only teachers can submit questions for approval."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        question = Question.objects.select_related(
            "created_by",
            "topic",
            "topic__domain",
            "topic__domain__course",
        ).get(id=question_id, created_by=user)
    except Question.DoesNotExist:
        return Response(
            {"detail": "Question not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    submittable_statuses = {
        Question.Status.DRAFT,
        Question.Status.REJECTED,
    }
    if question.status not in submittable_statuses:
        return Response(
            {"detail": "Only draft or rejected questions can be submitted for approval."},
            status=status.HTTP_400_BAD_REQUEST
        )

    prev = snapshot_question(question)
    question.status = Question.Status.SUBMITTED
    question.submitted_at = timezone.now()
    question.reviewed_by = None
    question.reviewed_at = None
    question.rejection_reason = ""
    question.is_active = False
    question.approved_by = None
    question.approved_at = None
    question.save(
        update_fields=[
            "status",
            "submitted_at",
            "reviewed_by",
            "approved_by",
            "reviewed_at",
            "approved_at",
            "rejection_reason",
            "is_active",
        ]
    )
    log_action(
        user=user,
        action=AuditLog.Action.SUBMITTED,
        entity_type="question",
        entity_id=question.id,
        previous_value=prev,
        new_value=snapshot_question(question),
        description=f"Teacher {user.username} submitted question for approval.",
    )

    serializer = QuestionSerializer(question)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pending_question_approvals(request):
    user = request.user

    if not is_department_head_user(user):
        return Response(
            {"detail": "Only department heads can view pending approvals."},
            status=status.HTTP_403_FORBIDDEN
        )

    department = get_user_department(user)
    if not department:
        return Response(
            {"detail": "Department head has no department assigned."},
            status=status.HTTP_400_BAD_REQUEST
        )

    questions = Question.objects.filter(
        status=Question.Status.SUBMITTED,
        topic__domain__course__department=department
    ).select_related(
        "created_by",
        "topic",
        "topic__domain",
        "topic__domain__course",
        "topic__domain__course__department",
    ).prefetch_related("choices")

    serializer = QuestionSerializer(questions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve_question(request, question_id):
    user = request.user

    try:
        question = Question.objects.select_related(
            "topic",
            "topic__domain",
            "topic__domain__course",
            "topic__domain__course__department",
        ).get(id=question_id)
    except Question.DoesNotExist:
        return Response(
            {"detail": "Question not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if is_system_admin_user(user):
        return Response(
            {"detail": "System admins cannot academically approve questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    if not can_review_question(user, question):
        return Response(
            {"detail": "You can approve only questions in your department."},
            status=status.HTTP_403_FORBIDDEN
        )

    if question.status != Question.Status.SUBMITTED:
        return Response(
            {"detail": "Only submitted questions can be approved."},
            status=status.HTTP_400_BAD_REQUEST
        )

    duplicate_decision_response = resolve_duplicate_decision(request, question)
    if duplicate_decision_response is not None:
        return duplicate_decision_response

    mark_question_approved(question, user)
    source_extracted = getattr(question, "source_extracted_question", None)
    if source_extracted:
        source_extracted.status = ExtractedQuestion.Status.APPROVED
        source_extracted.save(update_fields=["status"])

        exam_import = source_extracted.exam_import
        if not exam_import.extracted_questions.exclude(
            status=ExtractedQuestion.Status.APPROVED
        ).exists():
            exam_import.status = ExamPdfImport.Status.APPROVED
            exam_import.save(update_fields=["status"])

    log_action(
        user=user,
        action=AuditLog.Action.APPROVED,
        entity_type="question",
        entity_id=question.id,
        new_value=snapshot_question(question),
        description=f"Dept Head {user.username} approved question.",
    )

    serializer = QuestionSerializer(question)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_question(request, question_id):
    user = request.user

    serializer = RejectQuestionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        question = Question.objects.select_related(
            "topic",
            "topic__domain",
            "topic__domain__course",
            "topic__domain__course__department",
        ).get(id=question_id)
    except Question.DoesNotExist:
        return Response(
            {"detail": "Question not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if is_system_admin_user(user):
        return Response(
            {"detail": "System admins cannot academically reject questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    if not can_review_question(user, question):
        return Response(
            {"detail": "You can reject only questions in your department."},
            status=status.HTTP_403_FORBIDDEN
        )

    if question.status != Question.Status.SUBMITTED:
        return Response(
            {"detail": "Only submitted questions can be rejected."},
            status=status.HTTP_400_BAD_REQUEST
        )

    question.status = Question.Status.REJECTED
    question.reviewed_by = user
    question.reviewed_at = timezone.now()
    question.approved_by = None
    question.approved_at = None
    question.rejection_reason = serializer.validated_data["rejection_reason"]
    question.is_active = False
    question.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "is_active",
        ]
    )
    source_extracted = getattr(question, "source_extracted_question", None)
    if source_extracted:
        source_extracted.status = ExtractedQuestion.Status.REJECTED
        source_extracted.save(update_fields=["status"])

    log_action(
        user=user,
        action=AuditLog.Action.REJECTED,
        entity_type="question",
        entity_id=question.id,
        new_value={
            **snapshot_question(question),
            "rejection_reason": question.rejection_reason,
        },
        description=f"Dept Head {user.username} rejected question: {question.rejection_reason[:100]}",
    )

    response_serializer = QuestionSerializer(question)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


class ChoiceViewSet(viewsets.ModelViewSet):
    serializer_class = ChoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Choice.objects.select_related(
            "question",
            "question__created_by",
            "question__topic__domain__course__department",
        )

        if is_teacher_user(user):
            assigned_course_ids = TeacherCourseAssignment.objects.filter(
                teacher=user
            ).values_list("course_id", flat=True)
            return queryset.filter(
                question__created_by=user,
                question__status__in=[
                    Question.Status.DRAFT,
                    Question.Status.REJECTED,
                ],
                question__topic__domain__course_id__in=assigned_course_ids,
            )

        if is_department_head_user(user):
            department = get_user_department(user)
            if not department:
                return queryset.none()

            return queryset.filter(
                question__topic__domain__course__department=department
            )

        if is_system_admin_user(user) or user.is_staff:
            return queryset

        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        question = serializer.validated_data["question"]
        if question.status == Question.Status.APPROVED:
            raise PermissionDenied("Cannot modify choices for approved questions.")
        if not (
            is_teacher_user(user)
            and question.created_by_id == user.id
            and question.status in {Question.Status.DRAFT, Question.Status.REJECTED}
            and teacher_can_use_topic(user, question.topic)
        ):
            raise PermissionDenied("Teachers can manage choices only for their own draft or rejected assigned-course questions.")
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        choice = self.get_object()
        question = serializer.validated_data.get("question", choice.question)
        if question.status == Question.Status.APPROVED:
            raise PermissionDenied("Cannot modify choices for approved questions.")
        if not (
            is_teacher_user(user)
            and question.created_by_id == user.id
            and question.status in {Question.Status.DRAFT, Question.Status.REJECTED}
            and teacher_can_use_topic(user, question.topic)
        ):
            raise PermissionDenied("Teachers can manage choices only for their own draft or rejected assigned-course questions.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        question = instance.question
        if question.status == Question.Status.APPROVED:
            raise PermissionDenied("Cannot modify choices for approved questions.")
        if not (
            is_teacher_user(user)
            and question.created_by_id == user.id
            and question.status in {Question.Status.DRAFT, Question.Status.REJECTED}
            and teacher_can_use_topic(user, question.topic)
        ):
            raise PermissionDenied("Teachers can delete choices only for their own draft or rejected assigned-course questions.")
        instance.delete()


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
            return ExamBlueprint.objects.select_related(
                "course", "created_by"
            ).prefetch_related("domain_rules").order_by("-created_at")
        return ExamBlueprint.objects.filter(is_active=True).order_by("-created_at")

    def perform_create(self, serializer):
        blueprint = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action=AuditLog.Action.BLUEPRINT_CHANGED,
            entity_type="blueprint",
            entity_id=blueprint.id,
            new_value=snapshot_blueprint(blueprint),
            description=f"Blueprint '{blueprint.title}' created.",
        )

    def perform_update(self, serializer):
        blueprint = self.get_object()
        prev = snapshot_blueprint(blueprint)
        updated = serializer.save()
        log_action(
            user=self.request.user,
            action=AuditLog.Action.BLUEPRINT_CHANGED,
            entity_type="blueprint",
            entity_id=updated.id,
            previous_value=prev,
            new_value=snapshot_blueprint(updated),
            description=f"Blueprint '{updated.title}' updated.",
        )


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
                is_correct=is_correct,
                response_time_seconds=0
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

        cache.delete(f"student_weakness_{user.id}")
        cache.delete(f"student_trend_{user.id}")

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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = ExamPdfImport.objects.select_related(
            "course",
            "course__department",
            "uploaded_by",
            "submitted_by",
        )

        if is_teacher_user(user):
            assigned_course_ids = TeacherCourseAssignment.objects.filter(
                teacher=user
            ).values_list("course_id", flat=True)
            return queryset.filter(
                uploaded_by=user,
                course_id__in=assigned_course_ids
            ).order_by("-uploaded_at")

        if is_system_admin_user(user) or user.is_staff:
            return queryset.all().order_by("-uploaded_at")

        if is_department_head_user(user):
            department = get_user_department(user)
            if department:
                return queryset.filter(
                    course__department=department
                ).order_by("-uploaded_at")

        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        course = serializer.validated_data["course"]

        if is_teacher_user(user):
            if not teacher_is_assigned_to_course(user, course.id):
                raise PermissionDenied(
                    "Teachers can upload exam PDFs only for assigned courses."
                )
        elif is_department_head_user(user):
            department = get_user_department(user)
            if not department or course.department_id != department.id:
                raise PermissionDenied(
                    "Department heads can upload PDFs only for their department."
                )
        elif not (is_system_admin_user(user) or user.is_staff):
            raise PermissionDenied("You do not have permission to upload exam PDFs.")

        serializer.save(uploaded_by=user)


class ExtractedQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = ExtractedQuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = ExtractedQuestion.objects.select_related(
            "exam_import",
            "exam_import__course",
            "exam_import__course__department",
            "exam_import__uploaded_by",
            "domain",
            "topic",
            "approved_question",
        )

        if is_teacher_user(user):
            assigned_course_ids = TeacherCourseAssignment.objects.filter(
                teacher=user
            ).values_list("course_id", flat=True)
            return queryset.filter(
                exam_import__uploaded_by=user,
                exam_import__course_id__in=assigned_course_ids
            ).order_by("-created_at")

        if is_system_admin_user(user) or user.is_staff:
            return queryset.all().order_by("-created_at")

        if is_department_head_user(user):
            department = get_user_department(user)
            if department:
                return queryset.filter(
                    exam_import__course__department=department
                ).order_by("-created_at")

        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        exam_import = serializer.validated_data["exam_import"]

        if not user_can_access_import(user, exam_import):
            raise PermissionDenied(
                "You can create extracted questions only for accessible imports."
            )

        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        extracted = self.get_object()
        topic = serializer.validated_data.get("topic", extracted.topic)
        domain = serializer.validated_data.get("domain", extracted.domain)

        if topic and topic.domain.course_id != extracted.exam_import.course_id:
            raise PermissionDenied("Topic must belong to the imported PDF course.")

        if domain and domain.course_id != extracted.exam_import.course_id:
            raise PermissionDenied("Domain must belong to the imported PDF course.")

        if is_teacher_user(user):
            if not (
                user_can_access_import(user, extracted.exam_import)
                and extracted.status in {
                    ExtractedQuestion.Status.DRAFT,
                    ExtractedQuestion.Status.REJECTED,
                }
            ):
                raise PermissionDenied(
                    "Teachers can edit only their own draft or rejected extracted questions."
                )
        elif is_department_head_user(user):
            if not user_can_access_import(user, extracted.exam_import):
                raise PermissionDenied(
                    "Department heads can edit only imports in their department."
                )
        elif not (is_system_admin_user(user) or user.is_staff):
            raise PermissionDenied("You do not have permission to edit this question.")

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if not (
            is_teacher_user(user)
            and user_can_access_import(user, instance.exam_import)
            and instance.status in {
                ExtractedQuestion.Status.DRAFT,
                ExtractedQuestion.Status.REJECTED,
            }
        ):
            raise PermissionDenied(
                "Teachers can delete only their own draft or rejected extracted questions."
            )

        instance.delete()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def process_exam_pdf_import(request, import_id):
    user = request.user

    try:
        exam_import = ExamPdfImport.objects.select_related(
            "course",
            "course__department",
            "uploaded_by",
        ).get(id=import_id)
    except ExamPdfImport.DoesNotExist:
        return Response(
            {"detail": "Exam PDF import not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if not user_can_access_import(user, exam_import):
        return Response(
            {"detail": "You do not have permission to process this PDF import."},
            status=status.HTTP_403_FORBIDDEN
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

    if is_system_admin_user(user):
        return Response(
            {"detail": "System admins cannot academically approve questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    if not is_department_head_user(user):
        return Response(
            {"detail": "Only department heads can approve extracted questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        extracted = ExtractedQuestion.objects.select_related(
            "approved_question",
            "exam_import",
            "exam_import__uploaded_by",
            "topic",
            "topic__domain",
            "topic__domain__course",
            "topic__domain__course__department",
        ).get(id=extracted_question_id)
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

    if extracted.status != ExtractedQuestion.Status.SUBMITTED:
        return Response(
            {"detail": "Only submitted extracted questions can be approved."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not extracted.topic:
        return Response(
            {"detail": "Topic is required before approval."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not can_review_topic(user, extracted.topic):
        return Response(
            {"detail": "You can approve only questions in your department."},
            status=status.HTTP_403_FORBIDDEN
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
        question = extracted.approved_question

        if question and question.status == Question.Status.SUBMITTED:
            duplicate_decision_response = resolve_duplicate_decision(request, question)
            if duplicate_decision_response is not None:
                return duplicate_decision_response

            question.originating_pdf_import = extracted.exam_import
            question.source_type = Question.SourceType.IMPORTED
            question.uploaded_by = extracted.exam_import.uploaded_by
            mark_question_approved(question, user)
            question.save(update_fields=[
                "originating_pdf_import",
                "source_type",
                "uploaded_by",
            ])
        else:
            question = Question.objects.create(
                topic=extracted.topic,
                text=extracted.question_text,
                bloom_level=extracted.bloom_level,
                difficulty=extracted.difficulty,
                explanation=extracted.explanation,
                created_by=extracted.exam_import.uploaded_by or user,
                uploaded_by=extracted.exam_import.uploaded_by,
                reviewed_by=user,
                approved_by=user,
                originating_pdf_import=extracted.exam_import,
                source_type=Question.SourceType.IMPORTED,
                status=Question.Status.APPROVED,
                reviewed_at=timezone.now(),
                approved_at=timezone.now(),
                submitted_at=timezone.now(),
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

        log_action(
            user=user,
            action=AuditLog.Action.APPROVED,
            entity_type="question",
            entity_id=question.id,
            new_value=snapshot_question(question),
            description=f"Dept Head {user.username} approved imported PDF question.",
        )

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


def create_submitted_question_from_extracted(extracted, teacher):
    question = Question.objects.create(
        topic=extracted.topic,
        text=extracted.question_text,
        bloom_level=extracted.bloom_level,
        difficulty=extracted.difficulty,
        explanation=extracted.explanation,
        created_by=teacher,
        uploaded_by=extracted.exam_import.uploaded_by,
        reviewed_by=None,
        approved_by=None,
        originating_pdf_import=extracted.exam_import,
        source_type=Question.SourceType.IMPORTED,
        status=Question.Status.SUBMITTED,
        reviewed_at=None,
        approved_at=None,
        submitted_at=timezone.now(),
        is_active=False
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

    extracted.status = ExtractedQuestion.Status.SUBMITTED
    extracted.approved_question = question
    extracted.save(update_fields=["status", "approved_question"])

    log_action(
        user=teacher,
        action=AuditLog.Action.SUBMITTED,
        entity_type="question",
        entity_id=question.id,
        new_value=snapshot_question(question),
        description=(
            f"Teacher {teacher.username} submitted extracted PDF question "
            "for approval."
        ),
    )

    return question


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_extracted_questions_for_approval(request):
    user = request.user

    if not is_teacher_user(user):
        return Response(
            {"detail": "Only teachers can submit extracted questions for approval."},
            status=status.HTTP_403_FORBIDDEN
        )

    ids = request.data.get("ids", [])
    import_id = request.data.get("import_id")

    queryset = ExtractedQuestion.objects.filter(
        status__in=[
            ExtractedQuestion.Status.DRAFT,
            ExtractedQuestion.Status.REJECTED,
        ],
        exam_import__uploaded_by=user,
    ).select_related(
        "topic",
        "domain",
        "exam_import",
        "exam_import__course",
        "exam_import__course__department",
    )

    assigned_course_ids = TeacherCourseAssignment.objects.filter(
        teacher=user
    ).values_list("course_id", flat=True)
    queryset = queryset.filter(exam_import__course_id__in=assigned_course_ids)

    if import_id:
        queryset = queryset.filter(exam_import_id=import_id)

    if ids:
        queryset = queryset.filter(id__in=ids)

    submitted = []
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

            question = create_submitted_question_from_extracted(extracted, user)
            submitted.append({
                "extracted_question_id": extracted.id,
                "question_number": extracted.question_number,
                "question_id": question.id,
            })

        submitted_import_ids = set(
            item["extracted_question_id"] for item in submitted
        )

        if submitted:
            touched_imports = ExamPdfImport.objects.filter(
                extracted_questions__id__in=submitted_import_ids
            ).distinct()

            for exam_import in touched_imports:
                exam_import.status = ExamPdfImport.Status.SUBMITTED
                exam_import.submitted_by = user
                exam_import.submitted_at = timezone.now()
                exam_import.save(
                    update_fields=[
                        "status",
                        "submitted_by",
                        "submitted_at",
                    ]
                )

    return Response(
        {
            "message": "Extracted questions submitted for approval.",
            "submitted_count": len(submitted),
            "skipped_count": len(skipped),
            "submitted": submitted,
            "skipped": skipped,
        },
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_extracted_question(request, extracted_question_id):
    user = request.user

    if is_system_admin_user(user):
        return Response(
            {"detail": "System admins cannot academically reject questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    if not is_department_head_user(user):
        return Response(
            {"detail": "Only department heads can reject extracted questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        extracted = ExtractedQuestion.objects.select_related(
            "exam_import",
            "exam_import__course",
            "exam_import__course__department",
            "exam_import__uploaded_by",
        ).get(id=extracted_question_id)
    except ExtractedQuestion.DoesNotExist:
        return Response(
            {"detail": "Extracted question not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if extracted.status != ExtractedQuestion.Status.SUBMITTED:
        return Response(
            {"detail": "Only submitted extracted questions can be rejected."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user_can_access_import(user, extracted.exam_import):
        return Response(
            {"detail": "You can reject only imports in your department."},
            status=status.HTTP_403_FORBIDDEN
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

    # Both department heads, teachers, and system admins can view stats
    if not (is_admin_user(user) or is_teacher_user(user)):
        return Response(
            {"detail": "Only admin and teacher users can view dashboard statistics."},
            status=status.HTTP_403_FORBIDDEN
        )

    User = get_user_model()
    is_system_admin = is_system_admin_user(user)
    is_dept_head = is_department_head_user(user)
    user_department = get_user_department(user)

    course_id = request.query_params.get("course") or request.GET.get("course")
    scoped_course = None
    if course_id:
        try:
            scoped_course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        if not department_head_can_manage_course(user, scoped_course):
            return Response({"error": "Course not in your department."}, status=status.HTTP_403_FORBIDDEN)

    # Counts
    if scoped_course:
        student_ids = ExamAttempt.objects.filter(
            mock_exam__course=scoped_course
        ).values_list("student_id", flat=True).distinct()
        total_students = User.objects.filter(id__in=student_ids, role="student").count()
        total_teachers = TeacherCourseAssignment.objects.filter(course=scoped_course).count()
        total_department_heads = 0
        total_system_admins = 0
        total_courses = 1
        total_departments = 1
        total_domains = Domain.objects.filter(course=scoped_course).count()
        total_topics = Topic.objects.filter(domain__course=scoped_course).count()
    elif is_system_admin:
        total_students = User.objects.filter(role="student").count()
        total_teachers = User.objects.filter(role="teacher").count()
        total_department_heads = User.objects.filter(role="department_head").count()
        total_system_admins = User.objects.filter(role="system_admin").count()
        total_courses = Course.objects.count()
        total_departments = Department.objects.count()
        total_domains = Domain.objects.count()
        total_topics = Topic.objects.count()
    else:
        # Department-scoped counts for department heads
        total_students = User.objects.filter(
            role="student",
            department=user_department
        ).count()
        total_teachers = User.objects.filter(
            role="teacher",
            department=user_department
        ).count()
        total_department_heads = 0
        total_system_admins = 0
        total_courses = Course.objects.filter(department=user_department).count()
        total_departments = 1
        total_domains = Domain.objects.filter(course__department=user_department).count()
        total_topics = Topic.objects.filter(domain__course__department=user_department).count()

    # Filter questions based on role & course
    if scoped_course:
        total_questions = Question.objects.filter(
            topic__domain__course=scoped_course
        ).count()
        active_questions = Question.objects.filter(
            topic__domain__course=scoped_course,
            is_active=True,
            status=Question.Status.APPROVED
        ).count()
    elif is_system_admin:
        total_questions = Question.objects.count()
        active_questions = Question.objects.filter(
            is_active=True,
            status=Question.Status.APPROVED
        ).count()
    else:
        total_questions = Question.objects.filter(
            topic__domain__course__department=user_department
        ).count()
        active_questions = Question.objects.filter(
            topic__domain__course__department=user_department,
            is_active=True,
            status=Question.Status.APPROVED
        ).count()

    if scoped_course:
        total_mock_exams = MockExam.objects.filter(course=scoped_course).count()
        total_attempts = ExamAttempt.objects.filter(mock_exam__course=scoped_course).count()
        submitted_attempts = ExamAttempt.objects.filter(
            mock_exam__course=scoped_course,
            status=ExamAttempt.Status.SUBMITTED
        ).count()
        average_readiness = ReadinessScore.objects.filter(course=scoped_course).aggregate(
            avg_score=Avg("score")
        )["avg_score"]
        average_exam_score = ExamAttempt.objects.filter(mock_exam__course=scoped_course).aggregate(
            avg_score=Avg("total_score")
        )["avg_score"]
        pdf_import_stats = {
            "total": ExamPdfImport.objects.filter(course=scoped_course).count(),
            "uploaded": ExamPdfImport.objects.filter(course=scoped_course, status=ExamPdfImport.Status.UPLOADED).count(),
            "needs_review": ExamPdfImport.objects.filter(course=scoped_course, status=ExamPdfImport.Status.NEEDS_REVIEW).count(),
            "approved": ExamPdfImport.objects.filter(course=scoped_course, status=ExamPdfImport.Status.APPROVED).count(),
            "failed": ExamPdfImport.objects.filter(course=scoped_course, status=ExamPdfImport.Status.FAILED).count(),
        }
        extracted_question_stats = {
            "total": ExtractedQuestion.objects.filter(exam_import__course=scoped_course).count(),
            "draft": ExtractedQuestion.objects.filter(exam_import__course=scoped_course, status=ExtractedQuestion.Status.DRAFT).count(),
            "approved": ExtractedQuestion.objects.filter(exam_import__course=scoped_course, status=ExtractedQuestion.Status.APPROVED).count(),
            "rejected": ExtractedQuestion.objects.filter(exam_import__course=scoped_course, status=ExtractedQuestion.Status.REJECTED).count(),
        }
    elif is_system_admin:
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
    else:
        total_mock_exams = MockExam.objects.filter(
            course__department=user_department
        ).count()
        total_attempts = ExamAttempt.objects.filter(
            mock_exam__course__department=user_department
        ).count()
        submitted_attempts = ExamAttempt.objects.filter(
            mock_exam__course__department=user_department,
            status=ExamAttempt.Status.SUBMITTED
        ).count()
        average_readiness = ReadinessScore.objects.filter(
            course__department=user_department
        ).aggregate(
            avg_score=Avg("score")
        )["avg_score"]
        average_exam_score = ExamAttempt.objects.filter(
            mock_exam__course__department=user_department
        ).aggregate(
            avg_score=Avg("total_score")
        )["avg_score"]
        pdf_import_stats = {
            "total": ExamPdfImport.objects.filter(
                course__department=user_department
            ).count(),
            "uploaded": ExamPdfImport.objects.filter(
                course__department=user_department,
                status=ExamPdfImport.Status.UPLOADED
            ).count(),
            "needs_review": ExamPdfImport.objects.filter(
                course__department=user_department,
                status=ExamPdfImport.Status.NEEDS_REVIEW
            ).count(),
            "approved": ExamPdfImport.objects.filter(
                course__department=user_department,
                status=ExamPdfImport.Status.APPROVED
            ).count(),
            "failed": ExamPdfImport.objects.filter(
                course__department=user_department,
                status=ExamPdfImport.Status.FAILED
            ).count(),
        }
        extracted_question_stats = {
            "total": ExtractedQuestion.objects.filter(
                exam_import__course__department=user_department
            ).count(),
            "draft": ExtractedQuestion.objects.filter(
                exam_import__course__department=user_department,
                status=ExtractedQuestion.Status.DRAFT
            ).count(),
            "approved": ExtractedQuestion.objects.filter(
                exam_import__course__department=user_department,
                status=ExtractedQuestion.Status.APPROVED
            ).count(),
            "rejected": ExtractedQuestion.objects.filter(
                exam_import__course__department=user_department,
                status=ExtractedQuestion.Status.REJECTED
            ).count(),
        }

    # Question distribution
    if scoped_course:
        question_distribution_by_domain = Question.objects.values(
            "topic__domain__id",
            "topic__domain__name"
        ).filter(
            is_active=True,
            status=Question.Status.APPROVED,
            topic__domain__course=scoped_course
        ).annotate(
            total=Count("id")
        ).order_by("-total")
    elif is_system_admin:
        question_distribution_by_domain = Question.objects.values(
            "topic__domain__id",
            "topic__domain__name"
        ).filter(
            is_active=True,
            status=Question.Status.APPROVED
        ).annotate(
            total=Count("id")
        ).order_by("-total")
    else:
        question_distribution_by_domain = Question.objects.values(
            "topic__domain__id",
            "topic__domain__name"
        ).filter(
            is_active=True,
            status=Question.Status.APPROVED,
            topic__domain__course__department=user_department
        ).annotate(
            total=Count("id")
        ).order_by("-total")

    if scoped_course:
        performances = StudentTopicPerformance.objects.filter(
            total_attempts__gt=0,
            domain__course=scoped_course
        ).select_related(
            "student",
            "domain",
            "topic"
        )
        recent_attempts = ExamAttempt.objects.filter(
            mock_exam__course=scoped_course
        ).select_related(
            "student",
            "mock_exam",
            "mock_exam__course"
        ).order_by("-submitted_at")[:10]
    elif is_system_admin:
        performances = StudentTopicPerformance.objects.filter(
            total_attempts__gt=0
        ).select_related(
            "student",
            "domain",
            "topic"
        )
        recent_attempts = ExamAttempt.objects.select_related(
            "student",
            "mock_exam",
            "mock_exam__course"
        ).order_by("-submitted_at")[:10]
    else:
        performances = StudentTopicPerformance.objects.filter(
            total_attempts__gt=0,
            domain__course__department=user_department
        ).select_related(
            "student",
            "domain",
            "topic"
        )
        recent_attempts = ExamAttempt.objects.filter(
            mock_exam__course__department=user_department
        ).select_related(
            "student",
            "mock_exam",
            "mock_exam__course"
        ).order_by("-submitted_at")[:10]

    weakest_topics = sorted(
        performances,
        key=lambda item: item.accuracy
    )[:5]

    return Response(
        {
            "users": {
                "total_students": total_students,
                "total_teachers": total_teachers,
                "total_department_heads": total_department_heads,
                "total_system_admins": total_system_admins,
            },

            "academic_structure": {
                "total_departments": total_departments,
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

    if not (is_teacher_user(user) or is_department_head_user(user) or is_system_admin_user(user) or user.is_staff):
        return Response(
            {"detail": "You do not have permission to auto-classify extracted questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    import_id = request.data.get("import_id")

    queryset = ExtractedQuestion.objects.filter(
        status=ExtractedQuestion.Status.DRAFT
    ).select_related(
        "exam_import",
        "exam_import__course",
        "exam_import__course__department",
        "exam_import__uploaded_by",
    )

    if is_teacher_user(user):
        assigned_course_ids = TeacherCourseAssignment.objects.filter(
            teacher=user
        ).values_list("course_id", flat=True)
        queryset = queryset.filter(
            exam_import__uploaded_by=user,
            exam_import__course_id__in=assigned_course_ids,
        )
    elif is_department_head_user(user) and not is_system_admin_user(user):
        department = get_user_department(user)
        queryset = queryset.filter(
            exam_import__course__department=department
        ) if department else queryset.none()

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

    if is_system_admin_user(user):
        return Response(
            {"detail": "System admins cannot academically approve questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    if not is_department_head_user(user):
        return Response(
            {"detail": "Only department heads can bulk approve extracted questions."},
            status=status.HTTP_403_FORBIDDEN
        )

    import_id = request.data.get("import_id")
    ids = request.data.get("ids", [])
    auto_classify = request.data.get("auto_classify", True)

    queryset = ExtractedQuestion.objects.filter(
        status=ExtractedQuestion.Status.SUBMITTED
    ).select_related(
        "topic",
        "domain",
        "exam_import",
        "exam_import__course",
        "exam_import__course__department",
        "exam_import__uploaded_by",
        "approved_question",
    )

    department = get_user_department(user)
    queryset = queryset.filter(
        exam_import__course__department=department
    ) if department else queryset.none()

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
                reviewed_by=user,
                status=Question.Status.APPROVED,
                reviewed_at=timezone.now(),
                submitted_at=timezone.now(),
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
            is_active=True,
            status=Question.Status.APPROVED
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


# --------------------------------------------------
# Phase 2: Duplicate Detection
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def check_question_duplicate(request):
    """
    Check if a question text is a potential duplicate of existing questions.
    POST body: { "text": "...", "course_id": 1, "exclude_question_id": null, "threshold": 0.85 }
    """
    user = request.user
    if not (is_teacher_user(user) or is_department_head_user(user) or is_system_admin_user(user)):
        return Response(
            {"detail": "Permission denied."},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = DuplicateCheckSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    text = serializer.validated_data["text"]
    course_id = serializer.validated_data.get("course_id")
    exclude_id = serializer.validated_data.get("exclude_question_id")
    threshold = serializer.validated_data.get("threshold", 0.85)

    duplicates = find_duplicates(
        text=text,
        course_id=course_id,
        threshold=threshold,
        exclude_question_id=exclude_id,
    )

    return Response(
        {
            "has_duplicates": len(duplicates) > 0,
            "duplicates": duplicates,
        },
        status=status.HTTP_200_OK
    )


# --------------------------------------------------
# Phase 2: Question Search
# --------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def question_search(request):
    """
    Advanced question search with filtering.
    Query params: course, domain, topic, difficulty, status, teacher_id, keyword, page, page_size
    """
    user = request.user

    # Base queryset scoped by role
    queryset = Question.objects.select_related(
        "created_by",
        "reviewed_by",
        "topic",
        "topic__domain",
        "topic__domain__course",
        "topic__domain__course__department",
    ).prefetch_related("choices")

    if is_student_user(user):
        queryset = queryset.filter(is_active=True, status=Question.Status.APPROVED)
    elif is_teacher_user(user):
        # Teachers see their own questions, with optional filter override
        queryset = queryset.filter(created_by=user)
    elif is_department_head_user(user):
        department = get_user_department(user)
        if department:
            queryset = queryset.filter(topic__domain__course__department=department)
        else:
            queryset = queryset.none()
    elif is_system_admin_user(user) or user.is_staff:
        pass  # All questions
    else:
        return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    # Apply filters
    params = request.query_params

    course_id = params.get("course")
    if course_id:
        queryset = queryset.filter(topic__domain__course_id=course_id)

    domain_id = params.get("domain")
    if domain_id:
        queryset = queryset.filter(topic__domain_id=domain_id)

    topic_id = params.get("topic")
    if topic_id:
        queryset = queryset.filter(topic_id=topic_id)

    difficulty = params.get("difficulty")
    if difficulty:
        queryset = queryset.filter(difficulty=difficulty)

    question_status = params.get("status")
    if question_status:
        queryset = queryset.filter(status=question_status)

    teacher_id = params.get("teacher_id")
    if teacher_id and not is_teacher_user(user):
        queryset = queryset.filter(created_by_id=teacher_id)

    keyword = params.get("keyword", "").strip()
    if keyword:
        queryset = queryset.filter(text__icontains=keyword)

    bloom_level = params.get("bloom_level")
    if bloom_level:
        queryset = queryset.filter(bloom_level=bloom_level)

    queryset = queryset.order_by("-created_at")

    # Pagination
    page_size = min(int(params.get("page_size", 20)), 100)
    page = max(int(params.get("page", 1)), 1)
    offset = (page - 1) * page_size
    total = queryset.count()
    questions = queryset[offset: offset + page_size]

    serializer = QuestionSerializer(questions, many=True)
    return Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "results": serializer.data,
        },
        status=status.HTTP_200_OK
    )


# --------------------------------------------------
# Phase 2: Blueprint Validation
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_blueprint(request, blueprint_id):
    """
    Validate blueprint before activation.
    Checks: domain totals == total_questions, sufficient approved questions per domain.
    """
    user = request.user
    if not is_admin_user(user):
        return Response(
            {"detail": "Only department heads can validate blueprints."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        blueprint = ExamBlueprint.objects.prefetch_related(
            "domain_rules__domain"
        ).get(id=blueprint_id)
    except ExamBlueprint.DoesNotExist:
        return Response({"detail": "Blueprint not found."}, status=status.HTTP_404_NOT_FOUND)

    errors = []
    warnings = []

    domain_rules = list(blueprint.domain_rules.all())

    if not domain_rules:
        errors.append("Blueprint has no domain rules. Add at least one domain with a question count.")
        return Response({"valid": False, "errors": errors, "warnings": warnings})

    rule_total = sum(r.number_of_questions for r in domain_rules)

    if rule_total != blueprint.total_questions:
        errors.append(
            f"Domain rules total {rule_total} questions but blueprint requires "
            f"{blueprint.total_questions}. Adjust domain question counts."
        )

    for rule in domain_rules:
        available = Question.objects.filter(
            topic__domain=rule.domain,
            is_active=True,
            status=Question.Status.APPROVED
        ).count()

        if available < rule.number_of_questions:
            errors.append(
                f"{rule.domain.name} requires {rule.number_of_questions} questions "
                f"but only {available} approved questions exist."
            )
        elif available < rule.number_of_questions * 2:
            warnings.append(
                f"{rule.domain.name} has {available} approved questions for "
                f"{rule.number_of_questions} required — low diversity."
            )

    difficulty_dist = blueprint.difficulty_distribution
    if difficulty_dist:
        dist_total = sum(difficulty_dist.values())
        if abs(dist_total - 100) > 0.01 and dist_total != blueprint.total_questions:
            errors.append(
                f"Difficulty distribution values must sum to 100% or total questions ({blueprint.total_questions}). Got {dist_total}."
            )

    bloom_dist = blueprint.bloom_distribution
    if bloom_dist:
        bloom_total = sum(bloom_dist.values())
        if abs(bloom_total - 100) > 0.01 and bloom_total != blueprint.total_questions:
            errors.append(
                f"Bloom level distribution values must sum to 100% or total questions ({blueprint.total_questions}). Got {bloom_total}."
            )

    topic_rules = list(blueprint.topic_rules.all())
    if topic_rules:
        topic_total = sum(tr.question_count for tr in topic_rules)
        if topic_total > blueprint.total_questions:
            errors.append(
                f"Topic rules total {topic_total} questions, exceeding blueprint total of {blueprint.total_questions}."
            )

    pass_pct = float(blueprint.pass_percentage)
    if not (0 < pass_pct <= 100):
        errors.append(f"Pass percentage must be between 0 and 100 (got {pass_pct}).")

    is_valid = len(errors) == 0
    return Response(
        {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "blueprint_id": blueprint.id,
                "title": blueprint.title,
                "total_questions": blueprint.total_questions,
                "domain_rule_total": rule_total,
                "domain_count": len(domain_rules),
            }
        },
        status=status.HTTP_200_OK
    )


# --------------------------------------------------
# Phase 2: Exam Bank Dashboard Stats
# --------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def exam_bank_stats(request):
    """
    Exam Bank statistics for Department Head dashboard.
    Returns question counts by status, course, domain, topic, and recent activity.
    """
    user = request.user
    if not is_admin_user(user):
        return Response(
            {"detail": "Only department heads can view exam bank stats."},
            status=status.HTTP_403_FORBIDDEN
        )

    department = get_user_department(user)
    is_sys_admin = is_system_admin_user(user)

    # Base question queryset
    if is_sys_admin:
        q_base = Question.objects
    elif department:
        q_base = Question.objects.filter(topic__domain__course__department=department)
    else:
        q_base = Question.objects.none()

    status_counts = {
        "total": q_base.count(),
        "approved": q_base.filter(status=Question.Status.APPROVED).count(),
        "pending": q_base.filter(status=Question.Status.SUBMITTED).count(),
        "draft": q_base.filter(status=Question.Status.DRAFT).count(),
        "rejected": q_base.filter(status=Question.Status.REJECTED).count(),
        "archived": q_base.filter(status=Question.Status.ARCHIVED).count(),
    }

    # Questions by course
    by_course_qs = q_base.values(
        "topic__domain__course__id",
        "topic__domain__course__name"
    ).annotate(count=Count("id")).order_by("-count")

    by_course = [
        {
            "course_id": r["topic__domain__course__id"],
            "course": r["topic__domain__course__name"],
            "count": r["count"],
        }
        for r in by_course_qs
    ]

    # Questions by domain
    by_domain_qs = q_base.values(
        "topic__domain__id",
        "topic__domain__name"
    ).annotate(count=Count("id")).order_by("-count")

    by_domain = [
        {
            "domain_id": r["topic__domain__id"],
            "domain": r["topic__domain__name"],
            "count": r["count"],
        }
        for r in by_domain_qs
    ]

    # Questions by topic (top 20)
    by_topic_qs = q_base.values(
        "topic__id",
        "topic__name"
    ).annotate(count=Count("id")).order_by("-count")[:20]

    by_topic = [
        {
            "topic_id": r["topic__id"],
            "topic": r["topic__name"],
            "count": r["count"],
        }
        for r in by_topic_qs
    ]

    # Recent teacher activity (audit logs)
    audit_qs = AuditLog.objects.filter(
        entity_type="question"
    ).select_related("user").order_by("-timestamp")

    if not is_sys_admin and department:
        # Filter audit logs to questions in this department
        dept_question_ids = list(
            q_base.values_list("id", flat=True)[:500]
        )
        audit_qs = audit_qs.filter(entity_id__in=dept_question_ids)

    recent_activity = [
        {
            "id": log.id,
            "username": log.user.username if log.user else "System",
            "action": log.action,
            "entity_id": log.entity_id,
            "description": log.description,
            "timestamp": log.timestamp,
        }
        for log in audit_qs[:20]
    ]

    # Status distribution for pie chart
    status_distribution = [
        {"status": k, "count": v}
        for k, v in status_counts.items()
        if k != "total" and v > 0
    ]

    return Response(
        {
            "status_counts": status_counts,
            "status_distribution": status_distribution,
            "by_course": by_course,
            "by_domain": by_domain,
            "by_topic": by_topic,
            "recent_activity": recent_activity,
        },
        status=status.HTTP_200_OK
    )


# --------------------------------------------------
# Phase 2: Audit Logs
# --------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def audit_log_list(request):
    """
    List audit logs with optional filtering.
    Query params: entity_type, entity_id, action, user_id, page, page_size
    """
    user = request.user
    if not (is_department_head_user(user) or is_system_admin_user(user) or user.is_staff):
        return Response(
            {"detail": "Only department heads and system admins can view audit logs."},
            status=status.HTTP_403_FORBIDDEN
        )

    queryset = AuditLog.objects.select_related("user").order_by("-timestamp")

    # Scope dept heads to their department's questions/blueprints
    department = get_user_department(user)
    if is_department_head_user(user) and not is_system_admin_user(user) and department:
        dept_question_ids = list(
            Question.objects.filter(
                topic__domain__course__department=department
            ).values_list("id", flat=True)[:1000]
        )
        dept_blueprint_ids = list(
            ExamBlueprint.objects.filter(
                course__department=department
            ).values_list("id", flat=True)
        )
        queryset = queryset.filter(
            Q(entity_type="question", entity_id__in=dept_question_ids) |
            Q(entity_type="blueprint", entity_id__in=dept_blueprint_ids) |
            Q(entity_type="assignment")
        )

    params = request.query_params

    entity_type = params.get("entity_type")
    if entity_type:
        queryset = queryset.filter(entity_type=entity_type)

    entity_id = params.get("entity_id")
    if entity_id:
        queryset = queryset.filter(entity_id=entity_id)

    action = params.get("action")
    if action:
        queryset = queryset.filter(action=action)

    user_id = params.get("user_id")
    if user_id:
        queryset = queryset.filter(user_id=user_id)

    # Pagination
    page_size = min(int(params.get("page_size", 25)), 100)
    page = max(int(params.get("page", 1)), 1)
    offset = (page - 1) * page_size
    total = queryset.count()
    logs = queryset[offset: offset + page_size]

    serializer = AuditLogSerializer(logs, many=True)
    return Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size else 1,
            "results": serializer.data,
        },
        status=status.HTTP_200_OK
    )


# --------------------------------------------------
# System Admin Dedicated Endpoints
# --------------------------------------------------

@api_view(["GET", "PATCH"])
@permission_classes([IsSystemAdminOnly])
def system_settings(request):
    settings_obj = SystemSettings.get_solo()
    if request.method == "PATCH":
        for field in [
            "default_passing_score",
            "default_exam_duration_minutes",
            "max_battle_participants",
        ]:
            if field in request.data:
                setattr(settings_obj, field, int(request.data[field]))
        settings_obj.updated_by = request.user
        settings_obj.save()

        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.SYSTEM_SETTINGS_UPDATED,
            entity_type="system_settings",
            entity_id=settings_obj.id,
            new_value=request.data,
            description="System settings updated"
        )

    return Response({
        "default_passing_score": settings_obj.default_passing_score,
        "default_exam_duration_minutes": settings_obj.default_exam_duration_minutes,
        "max_battle_participants": settings_obj.max_battle_participants,
        "updated_at": settings_obj.updated_at,
    })


@api_view(["GET"])
@permission_classes([IsSystemAdminOnly])
def list_users(request):
    User = get_user_model()
    qs = User.objects.all().select_related("department")
    role = request.query_params.get("role")
    search = request.query_params.get("search")
    is_active = request.query_params.get("is_active")

    if role:
        qs = qs.filter(role=role)
    if search:
        qs = qs.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    if is_active is not None and is_active != "":
        qs = qs.filter(is_active=(is_active.lower() == "true"))

    qs = qs.order_by("-date_joined")

    page_size = min(int(request.query_params.get("page_size", 10)), 100)
    page = max(int(request.query_params.get("page", 1)), 1)
    offset = (page - 1) * page_size
    total = qs.count()
    users_slice = qs[offset:offset + page_size]

    return Response({
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 1,
        "results": [{
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "department": u.department.name if u.department else None,
            "department_id": u.department_id,
            "is_active": u.is_active,
            "date_joined": u.date_joined,
        } for u in users_slice]
    })


@api_view(["POST"])
@permission_classes([IsSystemAdminOnly])
def toggle_user_active(request, user_id):
    User = get_user_model()
    try:
        target = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    if target.id == request.user.id:
        return Response(
            {"error": "You cannot deactivate your own account."},
            status=status.HTTP_400_BAD_REQUEST
        )

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])

    action = (
        AuditLog.Action.USER_DEACTIVATED
        if not target.is_active
        else AuditLog.Action.USER_REACTIVATED
    )
    AuditLog.objects.create(
        user=request.user,
        action=action,
        entity_type="user",
        entity_id=target.id,
        new_value={
            "target_user_id": target.id,
            "target_username": target.username,
            "is_active": target.is_active,
        },
        description=f"{'Deactivated' if not target.is_active else 'Reactivated'} user {target.username}"
    )

    return Response({"id": target.id, "is_active": target.is_active})


@api_view(["POST"])
@permission_classes([IsSystemAdminOnly])
def admin_reset_password(request, user_id):
    User = get_user_model()
    try:
        target = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    new_password = request.data.get("new_password")
    if not new_password or len(new_password) < 8:
        return Response(
            {"error": "Password must be at least 8 characters."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        validate_password(new_password, target)
    except DjangoValidationError as e:
        return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)

    target.set_password(new_password)
    target.save(update_fields=["password"])

    AuditLog.objects.create(
        user=request.user,
        action=AuditLog.Action.PASSWORD_RESET_BY_ADMIN,
        entity_type="user",
        entity_id=target.id,
        new_value={"target_user_id": target.id, "target_username": target.username},
        description=f"Admin reset password for user {target.username}"
    )

    return Response({"message": f"Password reset for {target.username}."})


@api_view(["PATCH", "DELETE"])
@permission_classes([IsSystemAdminOnly])
def admin_department_detail(request, pk):
    try:
        dept = Department.objects.annotate(course_count=Count("courses")).get(pk=pk)
    except Department.DoesNotExist:
        return Response({"error": "Department not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "PATCH":
        serializer = DepartmentSerializer(dept, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    elif request.method == "DELETE":
        if dept.courses.exists():
            return Response(
                {"error": "Cannot delete department with existing courses."},
                status=status.HTTP_400_BAD_REQUEST
            )
        dept.delete()
        return Response(
            {"message": "Department deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


@api_view(["GET"])
@permission_classes([IsSystemAdminOnly])
def admin_audit_log_list(request):
    queryset = AuditLog.objects.select_related("user").order_by("-timestamp")
    params = request.query_params

    action = params.get("action")
    if action:
        queryset = queryset.filter(action=action)

    actor = params.get("actor") or params.get("user_id")
    if actor:
        queryset = queryset.filter(user_id=actor)

    entity_type = params.get("entity_type")
    if entity_type:
        queryset = queryset.filter(entity_type=entity_type)

    page_size = min(int(params.get("page_size", 25)), 100)
    page = max(int(params.get("page", 1)), 1)
    offset = (page - 1) * page_size
    total = queryset.count()
    logs = queryset[offset: offset + page_size]

    serializer = AuditLogSerializer(logs, many=True)
    return Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size else 1,
            "results": serializer.data,
        },
        status=status.HTTP_200_OK
    )

