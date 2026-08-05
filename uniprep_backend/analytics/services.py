from datetime import timedelta
from django.utils import timezone
from django.conf import settings

from .models import (
    StudentTopicPerformance,
    SpacedRepetitionQueue,
    ReadinessScore,
    Notification,
)
from .notification_service import notify_user
from exit_exams.models import Topic


def update_topic_performance(student, question, is_correct, response_time_seconds=0):
    topic = question.topic
    domain = topic.domain

    performance, created = StudentTopicPerformance.objects.get_or_create(
        student=student,
        topic=topic,
        defaults={
            "domain": domain,
            "correct_attempts": 0,
            "wrong_attempts": 0,
            "total_attempts": 0,
            "average_time_seconds": 0,
            "trend": StudentTopicPerformance.Trend.STABLE,
        }
    )

    previous_accuracy = performance.accuracy
    previous_total = performance.total_attempts
    performance.domain = domain
    performance.total_attempts += 1

    if is_correct:
        performance.correct_attempts += 1
    else:
        performance.wrong_attempts += 1

    if response_time_seconds and response_time_seconds > 0:
        previous_time_total = performance.average_time_seconds * previous_total
        performance.average_time_seconds = round(
            (previous_time_total + response_time_seconds) / performance.total_attempts
        )

    new_accuracy = performance.accuracy

    if previous_total == 0:
        performance.trend = StudentTopicPerformance.Trend.STABLE
    elif new_accuracy > previous_accuracy:
        performance.trend = StudentTopicPerformance.Trend.IMPROVING
    elif new_accuracy < previous_accuracy:
        performance.trend = StudentTopicPerformance.Trend.DECLINING
    else:
        performance.trend = StudentTopicPerformance.Trend.STABLE

    performance.save()

    weak_threshold = 50
    min_attempts_for_weak_alert = 3
    was_weak = (
        previous_total >= min_attempts_for_weak_alert
        and previous_accuracy < weak_threshold
    )
    is_weak_now = (
        performance.total_attempts >= min_attempts_for_weak_alert
        and performance.accuracy < weak_threshold
    )
    if is_weak_now and not was_weak:
        already_alerted = Notification.objects.filter(
            student=student,
            notification_type=Notification.NotificationType.WEAK_TOPIC,
            is_read=False,
        ).exists()
        if not already_alerted:
            notify_user(
                student,
                title=f"Weak Topic Detected: {topic.name}",
                message=(
                    f"Your accuracy on {topic.name} has dropped to "
                    f"{performance.accuracy}%. Start a focused learning path to improve it."
                ),
                notification_type=Notification.NotificationType.WEAK_TOPIC,
                target_url="/student/learning",
            )

    return performance


def add_wrong_question_to_spaced_repetition(student, question):
    topic = question.topic

    queue_item, created = SpacedRepetitionQueue.objects.get_or_create(
        student=student,
        question=question,
        defaults={
            "topic": topic,
            "next_review_date": timezone.now().date() + timedelta(days=1),
            "interval_days": 1,
            "mastery_level": 0,
            "is_active": True,
        }
    )

    if not created:
        queue_item.topic = topic
        queue_item.interval_days = 1
        queue_item.mastery_level = max(queue_item.mastery_level - 1, 0)
        queue_item.next_review_date = timezone.now().date() + timedelta(days=1)
        queue_item.is_active = True
        queue_item.save()

    return queue_item


def calculate_readiness_score(student, course):
    topics = Topic.objects.filter(domain__course=course)

    total_weight = 0
    weighted_total = 0

    for topic in topics:
        weight = float(topic.importance_weight)

        performance = StudentTopicPerformance.objects.filter(
            student=student,
            topic=topic
        ).first()

        if performance and performance.total_attempts > 0:
            topic_score = performance.accuracy
        else:
            topic_score = 0

        weighted_total += topic_score * weight
        total_weight += weight

    if total_weight == 0:
        readiness = 0
    else:
        readiness = round(weighted_total / total_weight, 2)

    readiness_obj, created = ReadinessScore.objects.update_or_create(
        student=student,
        course=course,
        defaults={
            "score": readiness
        }
    )

    return readiness_obj
