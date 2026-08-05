"""
Dedicated Teacher Analytics endpoint.

Every metric below derives from ONE base queryset:

    Question.objects.filter(
        created_by=request.user,
        topic_id__in=teacher_assigned_topic_ids(request.user)
    )

Nothing here is department-wide, "all teachers", or admin-scoped.

Endpoint: GET /api/analytics/teacher-dashboard/
Cache:    5 minutes per user, key `teacher_dashboard_<user_id>`.
"""
from datetime import timedelta
from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from exit_exams.models import (
    AttemptDetail,
    AuditLog,
    Domain,
    ExamAttempt,
    Question,
    SystemSettings,
    TeacherTopicAssignment,
    Topic,
)


CACHE_TIMEOUT_SECONDS = 300  # 5 minutes
CACHE_KEY_TEMPLATE = "teacher_dashboard_{user_id}"

# Bloom / difficulty enums mirrored from Question model so the response can
# surface zero-count buckets explicitly (useful for empty-state UI highlights).
BLOOM_LEVELS = [choice[0] for choice in Question.BloomLevel.choices]
DIFFICULTIES = [choice[0] for choice in Question.Difficulty.choices]
STATUS_LEVELS = [choice[0] for choice in Question.Status.choices]


# --------------------------------------------------------------------------
# Cache helpers
# --------------------------------------------------------------------------
def _cache_key(user):
    return CACHE_KEY_TEMPLATE.format(user_id=user.id)


def clear_teacher_dashboard_cache(user_or_id):
    """Invalidate the cached teacher analytics payload for a user.

    Accepts either a user instance or a numeric id. Safe to call with None.
    """
    if user_or_id is None:
        return
    user_id = getattr(user_or_id, "id", user_or_id)
    if not user_id:
        return
    cache.delete(CACHE_KEY_TEMPLATE.format(user_id=user_id))


def clear_teacher_dashboard_cache_for_question(question):
    """Invalidate the dashboard of whoever owns `question` (created_by)."""
    if question is not None and getattr(question, "created_by_id", None):
        clear_teacher_dashboard_cache(question.created_by_id)


# --------------------------------------------------------------------------
# Query param serializer
# --------------------------------------------------------------------------
class TeacherDashboardQuerySerializer(serializers.Serializer):
    """Validates optional query params for the teacher dashboard endpoint.

    Currently no params are accepted (everything is auto-scoped to the
    requesting user). The serializer exists to formalize the endpoint surface
    and to keep DRF-style input validation in one place if filters are added.
    """
    def validate(self, attrs):
        return attrs


# --------------------------------------------------------------------------
# Payload builder
# --------------------------------------------------------------------------
def build_teacher_dashboard(user):
    """Return the full teacher dashboard payload dict for `user`.

    Pure function: performs all DB reads. Caller is responsible for caching.
    """
    # Import lazily to avoid a circular import (exit_exams.views imports
    # analytics.services which is fine, but keeping it lazy is safest).
    from exit_exams.views import teacher_assigned_topic_ids

    assigned_topic_ids = teacher_assigned_topic_ids(user)

    if not assigned_topic_ids:
        return _empty_payload()

    base_qs = Question.objects.filter(
        created_by=user,
        topic_id__in=assigned_topic_ids,
    )

    payload = OrderedDict()
    payload["pipeline"] = _section_pipeline(base_qs)
    payload["coverage"] = _section_coverage(base_qs, assigned_topic_ids)
    payload["question_quality"] = _section_question_quality(base_qs)
    payload["student_impact"] = _section_student_impact(base_qs)
    payload["approval_history"] = _section_approval_history(base_qs)
    payload["activity_timeline"] = _section_activity_timeline(user, base_qs)
    payload["productivity"] = _section_productivity(user, base_qs)
    return payload


# --------------------------------------------------------------------------
# Empty payload returned when a teacher has no active topic assignments
# --------------------------------------------------------------------------
def _empty_payload():
    return OrderedDict([
        ("pipeline", {
            "total_questions": 0, "draft": 0, "submitted": 0,
            "approved": 0, "rejected": 0, "archived": 0,
            "approval_rate": 0.0, "rejection_rate": 0.0,
            "average_review_time_hours": 0.0,
        }),
        ("coverage", {
            "assigned_topics": 0, "topics_with_questions": 0,
            "topics_missing_questions": [],
            "questions_per_topic": [],
            "questions_per_domain": [],
            "questions_per_bloom_level": [
                {"bloom_level": b, "count": 0} for b in BLOOM_LEVELS
            ],
            "questions_per_difficulty": [
                {"difficulty": d, "count": 0} for d in DIFFICULTIES
            ],
        }),
        ("question_quality", {
            "times_used_total": 0, "most_missed": [],
            "easiest": [], "hardest": [],
        }),
        ("student_impact", {
            "total_student_attempts": 0, "unique_students": 0,
            "average_accuracy": 0.0, "average_score": 0.0,
            "pass_rate": 0.0, "trend": [],
        }),
        ("approval_history", {
            "recently_approved": [], "recently_rejected": [],
            "pending_review": [], "common_rejection_reasons": [],
            "average_approval_time_hours": 0.0,
        }),
        ("activity_timeline", []),
        ("productivity", {
            "this_month": {
                "created": 0, "approved": 0, "rejected": 0,
                "updated": 0, "submitted": 0,
            },
            "monthly_trend": [],
        }),
    ])


# --------------------------------------------------------------------------
# Section 1 — My Question Pipeline
# --------------------------------------------------------------------------
def _section_pipeline(base_qs):
    status_counts = dict(base_qs.values("status").annotate(c=Count("id")).values_list("status", "c"))

    approved = status_counts.get(Question.Status.APPROVED, 0)
    rejected = status_counts.get(Question.Status.REJECTED, 0)
    submitted_total = approved + rejected
    approval_rate = round((approved / submitted_total) * 100, 2) if submitted_total else 0.0
    rejection_rate = round((rejected / submitted_total) * 100, 2) if submitted_total else 0.0

    # Average review time over the questions that completed the
    # submitted -> reviewed-at/approved-at journey, computed in Python to
    # stay DB-portable (SQLite dev + Postgres prod).
    review_times = []
    for q in base_qs.filter(
        submitted_at__isnull=False, approved_at__isnull=False
    ).only("submitted_at", "approved_at"):
        delta = q.approved_at - q.submitted_at
        if delta.total_seconds() > 0:
            review_times.append(delta.total_seconds() / 3600.0)
    average_review_hours = round(sum(review_times) / len(review_times), 2) if review_times else 0.0

    return {
        "total_questions": base_qs.count(),
        "draft": status_counts.get(Question.Status.DRAFT, 0),
        "submitted": status_counts.get(Question.Status.SUBMITTED, 0),
        "approved": approved,
        "rejected": rejected,
        "archived": status_counts.get(Question.Status.ARCHIVED, 0),
        "approval_rate": approval_rate,
        "rejection_rate": rejection_rate,
        "average_review_time_hours": average_review_hours,
    }


# --------------------------------------------------------------------------
# Section 2 — Content Coverage
# --------------------------------------------------------------------------
def _section_coverage(base_qs, assigned_topic_ids):
    assigned_topics = Topic.objects.filter(id__in=assigned_topic_ids).select_related("domain")

    # Topics that have at least one question authored by this teacher.
    topics_with_qs = base_qs.values_list("topic_id", flat=True).distinct()
    topics_with_questions = topics_with_qs.count()

    topics_missing_questions = [
        {
            "topic_id": t.id,
            "topic_name": t.name,
            "domain_id": t.domain_id,
            "domain_name": t.domain.name,
        }
        for t in assigned_topics.exclude(id__in=list(topics_with_qs))
    ]

    questions_per_topic = list(
        base_qs.values(
            "topic_id", "topic__name", "topic__domain__name"
        ).annotate(count=Count("id")).order_by("-count")
    )
    questions_per_topic = [
        {
            "topic_id": row["topic_id"],
            "topic_name": row["topic__name"],
            "domain_name": row["topic__domain__name"],
            "count": row["count"],
        }
        for row in questions_per_topic
    ]

    questions_per_domain = list(
        base_qs.values("topic__domain__id", "topic__domain__name").annotate(
            count=Count("id")
        ).order_by("-count")
    )
    questions_per_domain = [
        {
            "domain_id": row["topic__domain__id"],
            "domain_name": row["topic__domain__name"],
            "count": row["count"],
        }
        for row in questions_per_domain
    ]

    bloom_counts = dict(
        base_qs.values("bloom_level").annotate(c=Count("id")).values_list("bloom_level", "c")
    )
    questions_per_bloom = [
        {"bloom_level": b, "count": bloom_counts.get(b, 0)} for b in BLOOM_LEVELS
    ]

    difficulty_counts = dict(
        base_qs.values("difficulty").annotate(c=Count("id")).values_list("difficulty", "c")
    )
    questions_per_difficulty = [
        {"difficulty": d, "count": difficulty_counts.get(d, 0)} for d in DIFFICULTIES
    ]

    return {
        "assigned_topics": assigned_topics.count(),
        "topics_with_questions": topics_with_questions,
        "topics_missing_questions": topics_missing_questions,
        "questions_per_topic": questions_per_topic,
        "questions_per_domain": questions_per_domain,
        "questions_per_bloom_level": questions_per_bloom,
        "questions_per_difficulty": questions_per_difficulty,
    }


# --------------------------------------------------------------------------
# Section 3 — Question Quality
# --------------------------------------------------------------------------
def _section_question_quality(base_qs):
    detail_qs = AttemptDetail.objects.filter(question__in=base_qs)

    times_used_total = detail_qs.count()

    per_question = list(
        detail_qs.values("question_id", "question__text").annotate(
            total=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
            wrong=Count("id", filter=Q(is_correct=False)),
            avg_response_time=Avg("response_time_seconds"),
        )
    )

    enriched = []
    for row in per_question:
        total = row["total"] or 0
        correct = row["correct"] or 0
        wrong = row["wrong"] or 0
        accuracy = round((correct / total) * 100, 2) if total else 0.0
        enriched.append({
            "question_id": row["question_id"],
            "text": (row["question__text"] or "")[:200],
            "total_attempts": total,
            "correct_count": correct,
            "wrong_count": wrong,
            "accuracy": accuracy,
            "avg_response_time_seconds": round(row["avg_response_time"] or 0, 2),
        })

    def sort_key_accuracy_desc(item):
        return (-item["accuracy"], -item["total_attempts"])

    def sort_key_accuracy_asc(item):
        return (item["accuracy"], -item["total_attempts"])

    def sort_key_wrong_desc(item):
        return (-item["wrong_count"], -item["total_attempts"])

    most_missed = [i for i in enriched if i["total_attempts"] > 0]
    most_missed.sort(key=sort_key_wrong_desc)
    most_missed = most_missed[:10]

    easiest = [i for i in enriched if i["total_attempts"] >= 1]
    easiest.sort(key=sort_key_accuracy_desc)
    easiest = easiest[:10]

    hardest = [i for i in enriched if i["total_attempts"] >= 1]
    hardest.sort(key=sort_key_accuracy_asc)
    hardest = hardest[:10]

    return {
        "times_used_total": times_used_total,
        "most_missed": most_missed,
        "easiest": easiest,
        "hardest": hardest,
    }


# --------------------------------------------------------------------------
# Section 4 — Student Impact
# --------------------------------------------------------------------------
def _section_student_impact(base_qs):
    detail_qs = AttemptDetail.objects.filter(question__in=base_qs)

    attempts_involving = (
        ExamAttempt.objects.filter(details__question__in=base_qs).distinct()
    )
    total_student_attempts = attempts_involving.count()
    unique_students = attempts_involving.values("student_id").distinct().count()

    detail_total = detail_qs.count()
    detail_correct = detail_qs.filter(is_correct=True).count()
    average_accuracy = (
        round((detail_correct / detail_total) * 100, 2) if detail_total else 0.0
    )

    # Per-attempt accuracy against THIS teacher's questions (the only fair
    # "score" interpretation since a teacher should not see whole-exam totals
    # that include questions authored by other teachers).
    per_attempt = list(
        detail_qs.values("attempt_id").annotate(
            total=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
        )
    )
    attempt_accs = [
        (p["correct"] / p["total"]) * 100 if p["total"] else 0.0
        for p in per_attempt
    ]
    average_score = (
        round(sum(attempt_accs) / len(attempt_accs), 2) if attempt_accs else 0.0
    )

    mastery_threshold = SystemSettings.get_solo().mastery_threshold_accuracy
    if attempt_accs:
        passed = sum(1 for a in attempt_accs if a >= mastery_threshold)
        pass_rate = round((passed / len(attempt_accs)) * 100, 2)
    else:
        pass_rate = 0.0

    # Last 30 days trend — one row per day that has any attempt detail.
    thirty_days_ago = timezone.now() - timedelta(days=30)
    trend_qs = (
        detail_qs.filter(attempt__started_at__gte=thirty_days_ago)
        .annotate(day=TruncDate("attempt__started_at"))
        .values("day")
        .annotate(
            attempts=Count("attempt_id", distinct=True),
            total_details=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
        )
        .order_by("day")
    )
    trend = []
    for row in trend_qs:
        td = row["total_details"] or 0
        acc = round((row["correct"] / td) * 100, 2) if td else 0.0
        trend.append({
            "date": row["day"].isoformat() if row["day"] else None,
            "attempts": row["attempts"],
            "average_accuracy": acc,
        })

    return {
        "total_student_attempts": total_student_attempts,
        "unique_students": unique_students,
        "average_accuracy": average_accuracy,
        "average_score": average_score,
        "pass_rate": pass_rate,
        "trend": trend,
    }


# --------------------------------------------------------------------------
# Section 5 — Approval History
# --------------------------------------------------------------------------
def _section_approval_history(base_qs):
    recently_approved = list(
        base_qs.filter(
            status=Question.Status.APPROVED, approved_at__isnull=False
        ).select_related("approved_by").order_by("-approved_at")[:10]
    )
    recently_approved = [
        {
            "question_id": q.id,
            "text": q.text[:200],
            "approved_at": q.approved_at,
            "approved_by_username": q.approved_by.username if q.approved_by else None,
            "topic_name": q.topic.name,
        }
        for q in recently_approved
    ]

    recently_rejected = list(
        base_qs.filter(
            status=Question.Status.REJECTED, reviewed_at__isnull=False
        ).select_related("reviewed_by").order_by("-reviewed_at")[:10]
    )
    recently_rejected = [
        {
            "question_id": q.id,
            "text": q.text[:200],
            "reviewed_at": q.reviewed_at,
            "reviewed_by_username": q.reviewed_by.username if q.reviewed_by else None,
            "rejection_reason": q.rejection_reason,
            "topic_name": q.topic.name,
        }
        for q in recently_rejected
    ]

    pending_review = list(
        base_qs.filter(status=Question.Status.SUBMITTED).order_by("-submitted_at")[:10]
    )
    pending_review = [
        {
            "question_id": q.id,
            "text": q.text[:200],
            "submitted_at": q.submitted_at,
            "topic_name": q.topic.name,
        }
        for q in pending_review
    ]

    rejection_reason_rows = list(
        base_qs.filter(status=Question.Status.REJECTED)
        .exclude(rejection_reason="")
        .exclude(rejection_reason__isnull=True)
        .values("rejection_reason")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )
    common_rejection_reasons = [
        {"reason": r["rejection_reason"], "count": r["count"]}
        for r in rejection_reason_rows
    ]

    # Average approval time = approved_at - submitted_at for those that were
    # approved. Computed in Python for DB portability.
    approval_times = []
    for q in base_qs.filter(
        submitted_at__isnull=False, approved_at__isnull=False
    ).only("submitted_at", "approved_at"):
        delta = q.approved_at - q.submitted_at
        if delta.total_seconds() > 0:
            approval_times.append(delta.total_seconds() / 3600.0)
    average_approval_time_hours = (
        round(sum(approval_times) / len(approval_times), 2)
        if approval_times else 0.0
    )

    return {
        "recently_approved": recently_approved,
        "recently_rejected": recently_rejected,
        "pending_review": pending_review,
        "common_rejection_reasons": common_rejection_reasons,
        "average_approval_time_hours": average_approval_time_hours,
    }


# --------------------------------------------------------------------------
# Section 6 — Activity Timeline
# --------------------------------------------------------------------------
def _section_activity_timeline(user, base_qs):
    question_ids = list(base_qs.values_list("id", flat=True)[:1000])
    assignment_ids = list(
        TeacherTopicAssignment.objects.filter(teacher=user).values_list("id", flat=True)
    )

    if not question_ids and not assignment_ids:
        # Fall back to "actions performed by this teacher".
        audit_qs = AuditLog.objects.filter(user=user)
    else:
        clauses = Q(user=user)
        if question_ids:
            clauses |= Q(entity_type="question", entity_id__in=question_ids)
        if assignment_ids:
            clauses |= Q(entity_type="topic_assignment", entity_id__in=assignment_ids)
            clauses |= Q(entity_type="assignment", entity_id__in=assignment_ids)
        audit_qs = AuditLog.objects.filter(clauses)

    audit_qs = audit_qs.select_related("user").order_by("-timestamp")[:20]

    return [
        {
            "id": log.id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "timestamp": log.timestamp,
            "description": log.description,
            "username": log.user.username if log.user else "System",
        }
        for log in audit_qs
    ]


# --------------------------------------------------------------------------
# Section 7 — Productivity
# --------------------------------------------------------------------------
def _section_productivity(user, base_qs):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    this_month = {
        "created": base_qs.filter(created_at__gte=month_start).count(),
        "submitted": base_qs.filter(submitted_at__gte=month_start).count(),
        "approved": base_qs.filter(approved_at__gte=month_start).count(),
        "rejected": base_qs.filter(
            status=Question.Status.REJECTED, reviewed_at__gte=month_start
        ).count(),
        "updated": AuditLog.objects.filter(
            user=user,
            action=AuditLog.Action.UPDATED,
            entity_type="question",
            timestamp__gte=month_start,
        ).count(),
    }

    # Monthly trend, last 6 months (including current).
    monthly_trend = []
    for i in range(5, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        month_str = f"{y:04d}-{m:02d}"
        monthly_trend.append({
            "month": month_str,
            "created": base_qs.filter(created_at__year=y, created_at__month=m).count(),
            "approved": base_qs.filter(approved_at__year=y, approved_at__month=m).count(),
            "rejected": (
                base_qs.filter(status=Question.Status.REJECTED)
                .filter(reviewed_at__year=y, reviewed_at__month=m)
                .count()
            ),
            "submitted": base_qs.filter(submitted_at__year=y, submitted_at__month=m).count(),
        })

    return {
        "this_month": this_month,
        "monthly_trend": monthly_trend,
    }


# --------------------------------------------------------------------------
# View
# --------------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def teacher_dashboard(request):
    """Return analytics scoped to the requesting teacher's authored questions
    inside their currently-assigned topics."""
    user = request.user

    if getattr(user, "role", None) != "teacher":
        return Response(
            {"detail": "Only teachers can view this dashboard."},
            status=status.HTTP_403_FORBIDDEN,
        )

    cache_key = _cache_key(user)
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached, status=status.HTTP_200_OK)

    payload = build_teacher_dashboard(user)
    cache.set(cache_key, payload, CACHE_TIMEOUT_SECONDS)
    return Response(payload, status=status.HTTP_200_OK)