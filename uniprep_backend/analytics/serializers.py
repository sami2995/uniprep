from rest_framework import serializers
from .models import (
    StudentTopicPerformance,
    SpacedRepetitionQueue,
    ReadinessScore,
    FocusSession
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