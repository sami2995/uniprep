from rest_framework import serializers
from .models import (
    StudentTopicPerformance,
    SpacedRepetitionQueue,
    ReadinessScore,
    FocusSession,
    Notification
)


class StudentTopicPerformanceSerializer(serializers.ModelSerializer):
    accuracy = serializers.ReadOnlyField()

    class Meta:
        model = StudentTopicPerformance
        fields = "__all__"


class SpacedRepetitionQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpacedRepetitionQueue
        fields = "__all__"


class ReadinessScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadinessScore
        fields = "__all__"
class FocusSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusSession
        fields = "__all__"
        read_only_fields = ["student", "started_at", "ended_at", "duration_minutes"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "student",
            "title",
            "message",
            "notification_type",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["student", "created_at"]


from .models import LearningPath, LearningStep


class LearningStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningStep
        fields = ["step_type", "completed", "completed_at", "score"]


class LearningPathSerializer(serializers.ModelSerializer):
    steps = LearningStepSerializer(many=True, read_only=True)

    class Meta:
        model = LearningPath
        fields = [
            "id",
            "topic",
            "subtopic",
            "priority",
            "status",
            "current_step",
            "steps",
            "created_at",
            "completed_at",
        ]
