"""Temporary verification: mock exam generation survives Redis broadcast failure."""
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status

from .models import ExamBlueprint, ExamBlueprintTopicRule, Question
from .tests import _create_test_hierarchy, _create_question, _create_student

REDIS_CHANNEL = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("127.0.0.1", 6379)]},
    }
}


@override_settings(CHANNEL_LAYERS=REDIS_CHANNEL)
class GenerateMockExamNotificationResilienceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.department, self.course, self.domain, self.topic = _create_test_hierarchy()
        self.student = _create_student(self.department)
        self.client.force_authenticate(user=self.student)
        for i in range(5):
            _create_question(self.topic, f"Approved {i}")

    def test_course_mode_succeeds_when_redis_unavailable(self):
        response = self.client.post(
            "/api/exit-exams/generate-mock-exam/",
            {"course_id": self.course.id, "total_questions": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("mock_exam", response.data)

    def test_blueprint_mode_succeeds_when_redis_unavailable(self):
        blueprint = ExamBlueprint.objects.create(
            course=self.course,
            title="Blueprint",
            total_questions=2,
            duration_minutes=30,
        )
        ExamBlueprintTopicRule.objects.create(
            blueprint=blueprint,
            topic=self.topic,
            question_count=2,
        )
        for i in range(2):
            _create_question(
                self.topic,
                f"BP {i}",
                source_type=Question.SourceType.IMPORTED,
            )
        response = self.client.post(
            "/api/exit-exams/generate-mock-exam/",
            {"blueprint_id": blueprint.id},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["mode"], "blueprint")

    def test_topic_mode_succeeds_when_redis_unavailable(self):
        response = self.client.post(
            "/api/exit-exams/generate-mock-exam/",
            {"topic_id": self.topic.id, "total_questions": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["mode"], "topic")
