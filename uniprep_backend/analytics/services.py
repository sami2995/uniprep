from datetime import timedelta
from django.utils import timezone

from .models import (
    StudentTopicPerformance,
    SpacedRepetitionQueue,
    ReadinessScore
)
from exit_exams.models import Topic


def update_topic_performance(student, question, is_correct):
    topic = question.topic
    domain = topic.domain

    performance, created = StudentTopicPerformance.objects.get_or_create(
        student=student,
        topic=topic,
        defaults={
            "domain": domain,
            "correct_attempts": 0,
            "total_attempts": 0,
        }
    )

    performance.domain = domain
    performance.total_attempts += 1

    if is_correct:
        performance.correct_attempts += 1

    performance.save()
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