from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q, Max
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import (
    StudentTopicPerformance,
    SpacedRepetitionQueue,
    ReadinessScore,
    FocusSession,
    Notification
)
from .serializers import (
    StudentTopicPerformanceSerializer,
    SpacedRepetitionQueueSerializer,
    ReadinessScoreSerializer,
    FocusSessionSerializer,
    NotificationSerializer
)
from exit_exams.models import AttemptDetail, Course, ExamAttempt, MockExam, Domain, Topic, Question
from exit_exams.views import (
    is_department_head_user,
    get_user_department,
    department_head_can_manage_course,
    verified_student_required,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def course_overview(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only department heads and admins can view course analytics."},
            status=status.HTTP_403_FORBIDDEN
        )

    course_id = request.query_params.get("course")
    if course_id:
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        if not department_head_can_manage_course(user, course):
            return Response({"error": "Course not in your department."}, status=status.HTTP_403_FORBIDDEN)

        courses = [course]
        course_name = course.name
    else:
        courses = scoped_courses_for_user(user)
        course_name = "All Courses"

    User = get_user_model()
    department = get_department_scope(user)

    if course_id:
        student_ids = ExamAttempt.objects.filter(
            mock_exam__course=course
        ).values_list("student_id", flat=True).distinct()
        students_count = User.objects.filter(id__in=student_ids, role="student").count()
    else:
        students_qs = User.objects.filter(role="student")
        if department:
            students_qs = students_qs.filter(department=department)
        students_count = students_qs.count()

    attempts = ExamAttempt.objects.filter(
        mock_exam__course__in=courses,
        status__in=[
            ExamAttempt.Status.SUBMITTED,
            ExamAttempt.Status.AUTO_SUBMITTED,
        ]
    )

    total_attempts = attempts.count()
    average_score = attempts.aggregate(avg_score=Avg("total_score"))["avg_score"]
    pass_mark = get_passing_score(course if course_id else None)
    passed = attempts.filter(total_score__gte=pass_mark).count()
    failed = attempts.filter(total_score__lt=pass_mark).count()

    pass_rate = round((passed / total_attempts) * 100, 2) if total_attempts else 0
    fail_rate = round((failed / total_attempts) * 100, 2) if total_attempts else 0

    return Response(
        {
            "course": course_name,
            "students": students_count,
            "average_score": round(float(average_score), 2) if average_score is not None else 0,
            "pass_rate": pass_rate,
            "fail_rate": fail_rate,
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def topic_difficulty(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only department heads and admins can view topic difficulty."},
            status=status.HTTP_403_FORBIDDEN
        )

    course_id = request.query_params.get("course")
    if course_id:
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        if not department_head_can_manage_course(user, course):
            return Response({"error": "Course not in your department."}, status=status.HTTP_403_FORBIDDEN)

        courses = [course]
    else:
        courses = scoped_courses_for_user(user)

    failures = AttemptDetail.objects.filter(
        attempt__status__in=[
            ExamAttempt.Status.SUBMITTED,
            ExamAttempt.Status.AUTO_SUBMITTED,
        ],
        question__topic__domain__course__in=courses,
        is_correct=False
    ).values(
        "question__topic__id",
        "question__topic__name"
    ).annotate(
        failure_count=Count("id")
    ).order_by("-failure_count", "question__topic__name")

    return Response(
        [
            {
                "topic": item["question__topic__name"],
                "failure_count": item["failure_count"],
            }
            for item in failures
        ],
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def score_trend(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only department heads and admins can view score trends."},
            status=status.HTTP_403_FORBIDDEN
        )

    course_id = request.query_params.get("course")
    if course_id:
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        if not department_head_can_manage_course(user, course):
            return Response({"error": "Course not in your department."}, status=status.HTTP_403_FORBIDDEN)

        courses = [course]
        course_name = course.name
    else:
        courses = scoped_courses_for_user(user)
        course_name = "All Courses"

    try:
        months_param = int(request.query_params.get("months", 6))
    except (ValueError, TypeError):
        months_param = 6

    months_param = max(1, min(12, months_param))

    cache_key = f"dept_score_trend_{user.id}_{course_id or 'all'}_{months_param}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data, status=status.HTTP_200_OK)

    now = timezone.now()
    trend_list = []

    for i in range(months_param - 1, -1, -1):
        # Calculate year and month for (now - i months)
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1

        month_str = f"{y:04d}-{m:02d}"

        attempts = ExamAttempt.objects.filter(
            mock_exam__course__in=courses,
            status__in=[ExamAttempt.Status.SUBMITTED, ExamAttempt.Status.AUTO_SUBMITTED],
            submitted_at__year=y,
            submitted_at__month=m
        )

        if not attempts.exists():
            trend_list.append({"month": month_str, "average_score": None})
        else:
            # Group by student and get their latest attempt score in this month
            latest_attempts = attempts.values("student_id").annotate(
                latest_time=Max("submitted_at")
            )
            scores = []
            for item in latest_attempts:
                latest_att = attempts.filter(
                    student_id=item["student_id"],
                    submitted_at=item["latest_time"]
                ).first()
                if latest_att and latest_att.total_score is not None:
                    scores.append(float(latest_att.total_score))

            if scores:
                avg_val = round(sum(scores) / len(scores), 2)
                trend_list.append({"month": month_str, "average_score": avg_val})
            else:
                trend_list.append({"month": month_str, "average_score": None})

    res_data = {
        "course": course_name,
        "trend": trend_list
    }

    cache.set(cache_key, res_data, 900)  # 15 minutes cache
    return Response(res_data, status=status.HTTP_200_OK)


def get_passing_score(course=None):
    from exit_exams.models import ExamBlueprint, SystemSettings
    if course:
        blueprint = ExamBlueprint.objects.filter(course=course, is_active=True).first()
        if blueprint and blueprint.pass_percentage is not None:
            return float(blueprint.pass_percentage)
    blueprint = ExamBlueprint.objects.filter(is_active=True).first()
    if blueprint and blueprint.pass_percentage is not None:
        return float(blueprint.pass_percentage)
    return float(SystemSettings.get_solo().default_passing_score)


def get_pass_mark_for_course(course=None):
    return get_passing_score(course)


def get_student_weakest_topic(student, course=None):
    perf_qs = StudentTopicPerformance.objects.filter(
        student=student,
        total_attempts__gt=0
    )
    if course:
        perf_qs = perf_qs.filter(domain__course=course)

    weakest_perf = perf_qs.order_by("correct_attempts").first()
    return weakest_perf.topic.name if weakest_perf else "N/A"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def at_risk_students(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only department heads and admins can view at-risk students."},
            status=status.HTTP_403_FORBIDDEN
        )

    course_id = request.query_params.get("course")
    if course_id:
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        if not department_head_can_manage_course(user, course):
            return Response({"error": "Course not in your department."}, status=status.HTTP_403_FORBIDDEN)

        courses = [course]
        course_name = course.name
    else:
        courses = scoped_courses_for_user(user)
        course_name = "All Courses"

    pass_mark = get_pass_mark_for_course(courses[0] if len(courses) == 1 else None)

    try:
        limit = int(request.query_params.get("limit", 20))
    except (ValueError, TypeError):
        limit = 20
    limit = max(1, min(50, limit))

    try:
        offset = int(request.query_params.get("offset", 0))
    except (ValueError, TypeError):
        offset = 0
    offset = max(0, offset)

    readiness_qs = ReadinessScore.objects.filter(
        course__in=courses,
        score__lt=pass_mark
    ).select_related("student", "course").order_by("score")

    total_at_risk = readiness_qs.count()
    paginated_items = readiness_qs[offset:offset + limit]

    student_list = []
    for item in paginated_items:
        student = item.student
        c = item.course

        # Latest attempt score
        latest_attempt = ExamAttempt.objects.filter(
            student=student,
            mock_exam__course=c,
            status__in=[ExamAttempt.Status.SUBMITTED, ExamAttempt.Status.AUTO_SUBMITTED]
        ).order_by("-submitted_at").first()

        latest_score = (
            round(float(latest_attempt.total_score), 2)
            if latest_attempt and latest_attempt.total_score is not None
            else round(float(item.score), 2)
        )

        # Reused weakest topic helper
        weakest_topic_name = get_student_weakest_topic(student, c)

        student_list.append({
            "student_id": student.id,
            "name": student.get_full_name() or student.username,
            "latest_score": latest_score,
            "weakest_topic": weakest_topic_name,
            "readiness_score": round(float(item.score), 2)
        })

    return Response(
        {
            "course": course_name,
            "pass_mark": pass_mark,
            "total_at_risk": total_at_risk,
            "students": student_list
        },
        status=status.HTTP_200_OK
    )


ADMIN_ROLES = {"department_head", "system_admin", "admin"}
STUDENT_ROLES = {"student"}


def is_department_head_user(user):
    return getattr(user, "role", None) in {"department_head", "admin"}


def is_admin_user(user):
    return user.is_staff or getattr(user, "role", None) in ADMIN_ROLES


def get_department_scope(user):
    if is_department_head_user(user) or getattr(user, "role", None) == "student":
        return getattr(user, "department", None)
    return None


def scoped_courses_for_user(user):
    queryset = Course.objects.all()
    department = get_department_scope(user)

    if department:
        queryset = queryset.filter(department=department)

    return queryset


def student_performance_queryset(user):
    return StudentTopicPerformance.objects.filter(
        student=user,
        total_attempts__gt=0
    ).select_related(
        "domain",
        "domain__course",
        "topic"
    ).order_by("domain__course__name", "domain__name", "topic__name")


def recommendation_actions():
    return [
        "Read AI Summary",
        "Practice Flashcards",
        "Take Quiz",
        "Review Study Material",
        "Retry Mock Exam",
    ]


class StudentTopicPerformanceViewSet(viewsets.ModelViewSet):
    serializer_class = StudentTopicPerformanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role in ADMIN_ROLES:
            return StudentTopicPerformance.objects.all()
        return StudentTopicPerformance.objects.filter(student=user)


class SpacedRepetitionQueueViewSet(viewsets.ModelViewSet):
    serializer_class = SpacedRepetitionQueueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if verified_student_required(self.request):
            return SpacedRepetitionQueue.objects.none()
        base_qs = SpacedRepetitionQueue.objects.select_related("question")
        if user.is_staff or user.role in ADMIN_ROLES:
            return base_qs.all()
        return base_qs.filter(
            student=user,
            question__status=Question.Status.APPROVED,
            question__is_active=True
        )


class ReadinessScoreViewSet(viewsets.ModelViewSet):
    serializer_class = ReadinessScoreSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role in ADMIN_ROLES:
            return ReadinessScore.objects.all()
        return ReadinessScore.objects.filter(student=user)


from django.core.cache import cache

def calculate_topic_trend_v2(user, topic):
    attempts = list(
        ExamAttempt.objects.filter(
            student=user,
            status__in=[ExamAttempt.Status.SUBMITTED, ExamAttempt.Status.AUTO_SUBMITTED]
        ).order_by("-submitted_at")[:3]
    )

    attempt_accuracies = []
    for att in attempts:
        details = AttemptDetail.objects.filter(attempt=att, question__topic=topic)
        total = details.count()
        if total > 0:
            correct = details.filter(is_correct=True).count()
            acc = round((correct / total) * 100)
            attempt_accuracies.append(acc)

    N = len(attempt_accuracies)

    if N < 2:
        return {
            "trend_direction": "no_data",
            "trend_arrow": "—",
            "attempts_analyzed": N,
            "previous_accuracy": None,
            "current_accuracy": attempt_accuracies[0] if N == 1 else None,
            "improvement_points": None,
            "improvement_label": "First attempt",
        }

    current_acc = attempt_accuracies[0]
    previous_acc = attempt_accuracies[-1]
    diff = current_acc - previous_acc

    if diff > 5:
        trend_dir = "improving"
        trend_arrow = "↑"
    elif diff < -5:
        trend_dir = "declining"
        trend_arrow = "↓"
    else:
        trend_dir = "stable"
        trend_arrow = "→"

    label_sign = "+" if diff > 0 else ""
    improvement_label = f"{label_sign}{diff} pts"

    return {
        "trend_direction": trend_dir,
        "trend_arrow": trend_arrow,
        "attempts_analyzed": N,
        "previous_accuracy": previous_acc,
        "current_accuracy": current_acc,
        "improvement_points": diff,
        "improvement_label": improvement_label,
    }


def get_recommendation_priority_v2(accuracy, trend_direction="stable"):
    acc = float(accuracy or 0)
    if acc < 30:
        return "high"
    elif acc <= 60:
        return "medium"
    else:
        return "low"


def trigger_spaced_repetition_for_high_priority(user, topic):
    q = Question.objects.filter(
        topic=topic,
        status=Question.Status.APPROVED,
        is_active=True
    ).first()

    if q:
        SpacedRepetitionQueue.objects.get_or_create(
            student=user,
            question=q,
            defaults={
                "topic": topic,
                "next_review_date": timezone.now().date() + timedelta(days=1),
                "interval_days": 1,
                "mastery_level": 0,
                "is_active": True,
            }
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_weakness(request):
    user = request.user

    if getattr(user, "role", None) not in STUDENT_ROLES:
        return Response(
            {"detail": "Only students can view weakness analytics."},
            status=status.HTTP_403_FORBIDDEN
        )

    cache_key = f"student_weakness_{user.id}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data, status=status.HTTP_200_OK)

    courses_list = scoped_courses_for_user(user)
    courses = []

    for course in courses_list:
        domains_list = Domain.objects.filter(course=course)
        domains_data = []

        for domain in domains_list:
            topics_in_domain = Topic.objects.filter(domain=domain)
            topics_data = []
            topic_accuracies = []

            for topic in topics_in_domain:
                perf = StudentTopicPerformance.objects.filter(student=user, topic=topic).first()

                if perf and perf.total_attempts > 0:
                    acc = perf.accuracy
                    total_att = perf.total_attempts
                    status_str = "weak" if acc < 60 else "strong"
                    topic_accuracies.append(acc)
                else:
                    acc = None
                    total_att = 0
                    status_str = "not_attempted"

                topics_data.append({
                    "topic": topic.name,
                    "topic_id": topic.id,
                    "accuracy": acc,
                    "total_attempts": total_att,
                    "status": status_str,
                    "correct": perf.correct_attempts if perf else 0,
                    "wrong": perf.wrong_attempts if perf else 0,
                    "average_time_seconds": perf.average_time_seconds if perf else 0,
                    "trend": perf.trend if perf else "stable",
                })

            domain_acc = (
                round(sum(topic_accuracies) / len(topic_accuracies))
                if topic_accuracies
                else 0
            )

            domains_data.append({
                "id": domain.id,
                "name": domain.name,
                "domain": domain.name,
                "accuracy": domain_acc,
                "topics": topics_data,
            })

        if domains_data:
            courses.append({
                "course": course.name,
                "domains": domains_data,
            })

    if not courses:
        res_data = {"course": None, "domains": [], "weak_domains": []}
    elif len(courses) == 1:
        res_data = {
            "course": courses[0]["course"],
            "domains": courses[0]["domains"],
            "weak_domains": [
                d for d in courses[0]["domains"] if d.get("accuracy", 100) < 60
            ]
        }
    else:
        all_weak_domains = []
        for c in courses:
            for d in c["domains"]:
                if d.get("accuracy", 100) < 60:
                    d_copy = dict(d)
                    d_copy["course"] = c["course"]
                    all_weak_domains.append(d_copy)
        res_data = {
            "courses": courses,
            "weak_domains": all_weak_domains,
        }

    cache.set(cache_key, res_data, 300)
    return Response(res_data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_trend(request):
    user = request.user

    if getattr(user, "role", None) not in STUDENT_ROLES:
        return Response(
            {"detail": "Only students can view trend analytics."},
            status=status.HTTP_403_FORBIDDEN
        )

    cache_key = f"student_trend_{user.id}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data, status=status.HTTP_200_OK)

    performances = student_performance_queryset(user)
    trend_list = []

    for performance in performances:
        trend_info = calculate_topic_trend_v2(user, performance.topic)
        trend_list.append({
            "topic": performance.topic.name,
            "topic_id": performance.topic.id,
            "domain": performance.domain.name,
            "accuracy": performance.accuracy,
            "trend": performance.trend,
            "trend_direction": trend_info["trend_direction"],
            "trend_arrow": trend_info["trend_arrow"],
            "attempts_analyzed": trend_info["attempts_analyzed"],
            "previous_accuracy": trend_info["previous_accuracy"],
            "current_accuracy": trend_info["current_accuracy"],
            "improvement_points": trend_info["improvement_points"],
            "improvement_label": trend_info["improvement_label"],
        })

    cache.set(cache_key, trend_list, 300)
    return Response(trend_list, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_recommendations(request):
    user = request.user

    if verified_student_required(request):
        return Response(
            {
                "error": (
                    "Your account is pending verification. You can use personal study "
                    "features, but exit exam content requires institutional verification."
                ),
                "verification_status": getattr(user, "verification", "pending"),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    if getattr(user, "role", None) not in STUDENT_ROLES:
        return Response(
            {"detail": "Only students can view recommendations."},
            status=status.HTTP_403_FORBIDDEN
        )

    all_performances = student_performance_queryset(user)
    fixed_sequence = [
        "Read AI Summary",
        "Practice Flashcards",
        "Take Quiz",
        "Retry Mock Exam"
    ]

    rec_list = []

    for performance in all_performances:
        trend_info = calculate_topic_trend_v2(user, performance.topic)
        priority = get_recommendation_priority_v2(
            performance.accuracy,
            trend_direction=trend_info["trend_direction"]
        )

        # Include if accuracy < 60 OR if >60 when trend_direction is declining
        if performance.accuracy < 60 or trend_info["trend_direction"] == "declining":
            if priority == "high":
                trigger_spaced_repetition_for_high_priority(user, performance.topic)

            rec_list.append({
                "topic": performance.topic.name,
                "topic_id": performance.topic.id,
                "domain": performance.domain.name,
                "accuracy": performance.accuracy,
                "recommendations": recommendation_actions(),
                "weakest_subtopic": performance.topic.name,
                "study_sequence": fixed_sequence,
                "priority": priority,
                "trend_direction": trend_info["trend_direction"],
                "trend_arrow": trend_info["trend_arrow"],
                "improvement_label": trend_info["improvement_label"],
            })

    return Response(rec_list, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def course_overview(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only department heads and admins can view course analytics."},
            status=status.HTTP_403_FORBIDDEN
        )

    User = get_user_model()
    courses = scoped_courses_for_user(user)
    course_filter = Q(mock_exam__course__in=courses)
    department = get_department_scope(user)

    students = User.objects.filter(role="student")
    if department:
        students = students.filter(department=department)

    attempts = ExamAttempt.objects.filter(
        course_filter,
        status__in=[
            ExamAttempt.Status.SUBMITTED,
            ExamAttempt.Status.AUTO_SUBMITTED,
        ]
    )

    total_attempts = attempts.count()
    average_score = attempts.aggregate(avg_score=Avg("total_score"))["avg_score"]
    pass_mark = get_passing_score()
    passed = attempts.filter(total_score__gte=pass_mark).count()
    failed = attempts.filter(total_score__lt=pass_mark).count()

    pass_rate = round((passed / total_attempts) * 100, 2) if total_attempts else 0
    fail_rate = round((failed / total_attempts) * 100, 2) if total_attempts else 0

    return Response(
        {
            "students": students.count(),
            "average_score": round(float(average_score), 2) if average_score is not None else 0,
            "pass_rate": pass_rate,
            "fail_rate": fail_rate,
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def topic_difficulty(request):
    user = request.user

    if not is_admin_user(user):
        return Response(
            {"detail": "Only department heads and admins can view topic difficulty."},
            status=status.HTTP_403_FORBIDDEN
        )

    courses = scoped_courses_for_user(user)

    failures = AttemptDetail.objects.filter(
        attempt__status__in=[
            ExamAttempt.Status.SUBMITTED,
            ExamAttempt.Status.AUTO_SUBMITTED,
        ],
        question__topic__domain__course__in=courses,
        is_correct=False
    ).values(
        "question__topic__id",
        "question__topic__name"
    ).annotate(
        failure_count=Count("id")
    ).order_by("-failure_count", "question__topic__name")

    return Response(
        [
            {
                "topic": item["question__topic__name"],
                "failure_count": item["failure_count"],
            }
            for item in failures
        ],
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notifications(request):
    queryset = Notification.objects.filter(
        student=request.user
    ).order_by("-created_at")[:20]

    serializer = NotificationSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(
            id=notification_id,
            student=request.user
        )
    except Notification.DoesNotExist:
        return Response(
            {"detail": "Notification not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    notification.is_read = True
    notification.save(update_fields=["is_read"])

    return Response(
        {"message": "Notification marked as read."},
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    updated = Notification.objects.filter(
        student=request.user,
        is_read=False
    ).update(is_read=True)

    return Response(
        {"message": "All notifications marked as read.", "updated_count": updated},
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_notification_count(request):
    count = Notification.objects.filter(
        student=request.user,
        is_read=False
    ).count()

    return Response({"unread_count": count}, status=status.HTTP_200_OK)




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

    topic_performance_data = []
    weak_topics_data = []
    domain_map = {}

    for performance in topic_performances:
        trend_metrics = calculate_topic_trend_v2(user, performance.topic)
        priority = get_recommendation_priority_v2(performance.accuracy)
        topic_info = {
            "topic_id": performance.topic.id,
            "topic": performance.topic.name,
            "domain_id": performance.domain.id,
            "domain": performance.domain.name,
            "accuracy": performance.accuracy,
            "correct_attempts": performance.correct_attempts,
            "total_attempts": performance.total_attempts,
            "trend": performance.trend,
            "trend_direction": trend_metrics["trend_direction"],
            "trend_arrow": trend_metrics["trend_arrow"],
            "improvement_points": trend_metrics["improvement_points"],
            "improvement_label": trend_metrics["improvement_label"],
            "priority": priority,
            "weakest_subtopic": performance.topic.name,
            "study_sequence": [
                "Read AI Summary",
                "Practice Flashcards",
                "Take Quiz",
                "Retry Mock Exam"
            ],
        }
        topic_performance_data.append(topic_info)

        if performance.total_attempts > 0 and performance.accuracy < 60:
            weak_topics_data.append(topic_info)

        d_entry = domain_map.setdefault(
            performance.domain.id,
            {
                "id": performance.domain.id,
                "name": performance.domain.name,
                "domain": performance.domain.name,
                "topics": [],
            }
        )
        d_entry["topics"].append(topic_info)

    weak_domains_data = []
    for d_data in domain_map.values():
        t_list = d_data["topics"]
        avg_acc = round(sum(t["accuracy"] for t in t_list) / len(t_list), 1) if t_list else 0.0
        weakest = min(t_list, key=lambda t: t["accuracy"]) if t_list else None
        d_data["accuracy"] = avg_acc
        d_data["priority"] = get_recommendation_priority_v2(avg_acc)
        d_data["weakest_subtopic"] = weakest["topic"] if weakest else "N/A"
        if avg_acc < 60:
            weak_domains_data.append(d_data)

    # Spaced repetition due today or earlier (approved active questions only)
    due_reviews = SpacedRepetitionQueue.objects.none()
    if not verified_student_required(request):
        due_reviews = SpacedRepetitionQueue.objects.filter(
            student=user,
            is_active=True,
            next_review_date__lte=timezone.now().date(),
            question__status=Question.Status.APPROVED,
            question__is_active=True
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

            "topic_performance": topic_performance_data,
            "weak_topics": weak_topics_data,
            "weak_domains": weak_domains_data,

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
                "today_minutes": round(today_focus_minutes, 1),
                "week_minutes": round(week_focus_minutes, 1),
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
    session.duration_minutes = round(seconds / 60, 2)

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
