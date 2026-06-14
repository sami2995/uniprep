from rest_framework import serializers

from .models import (
    QuizChallenge,
    ChallengeParticipant,
    ChallengeQuestion,
    ChallengeAttempt,
    ChallengeAttemptDetail,
)


class QuizChallengeSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True)
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True
    )
    participant_count = serializers.SerializerMethodField()

    class Meta:
        model = QuizChallenge
        fields = [
            "id",
            "room_code",
            "title",
            "course",
            "course_name",
            "created_by",
            "created_by_username",
            "total_questions",
            "duration_minutes",
            "status",
            "participant_count",
            "created_at",
            "started_at",
            "completed_at",
        ]
        read_only_fields = [
            "room_code",
            "created_by",
            "status",
            "created_at",
            "started_at",
            "completed_at",
        ]

    def get_participant_count(self, obj):
        return obj.participants.count()


class ChallengeParticipantSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="student.username", read_only=True)

    class Meta:
        model = ChallengeParticipant
        fields = [
            "id",
            "challenge",
            "student",
            "username",
            "joined_at",
            "is_creator",
        ]


class ChallengeQuestionSerializer(serializers.ModelSerializer):
    question_id = serializers.IntegerField(source="question.id", read_only=True)
    text = serializers.CharField(source="question.text", read_only=True)
    choices = serializers.SerializerMethodField()

    class Meta:
        model = ChallengeQuestion
        fields = [
            "id",
            "order",
            "question_id",
            "text",
            "choices",
        ]

    def get_choices(self, obj):
        return [
            {
                "id": choice.id,
                "text": choice.text,
            }
            for choice in obj.question.choices.all()
        ]


class ChallengeAttemptDetailSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.text", read_only=True)
    selected_answer = serializers.CharField(
        source="selected_choice.text",
        read_only=True
    )

    class Meta:
        model = ChallengeAttemptDetail
        fields = [
            "id",
            "question",
            "question_text",
            "selected_choice",
            "selected_answer",
            "is_correct",
            "response_time_seconds",
        ]


class ChallengeAttemptSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(
        source="student.username",
        read_only=True
    )
    details = ChallengeAttemptDetailSerializer(many=True, read_only=True)

    class Meta:
        model = ChallengeAttempt
        fields = [
            "id",
            "challenge",
            "student",
            "student_username",
            "score",
            "duration_seconds",
            "started_at",
            "submitted_at",
            "details",
        ]