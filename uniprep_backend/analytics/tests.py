"""
Tests for adaptive learning real quiz, mini mock, and weak topic practice.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from exit_exams.models import (
    Department,
    Course,
    Domain,
    Topic,
    Question,
    Choice,
    MockExam,
    ExamAttempt,
    AttemptDetail,
)
from analytics.models import (
    LearningPath,
    LearningStep,
    StudentTopicPerformance,
    ReadinessScore,
)
from analytics.adaptive_learning_service import (
    generate_learning_path,
    generate_adaptive_quiz,
    evaluate_adaptive_quiz,
)

User = get_user_model()


def _create_test_hierarchy():
    department = Department.objects.create(name="Test Dept", code="TSTD")
    course = Course.objects.create(name="Test Course", department=department)
    domain = Domain.objects.create(name="Test Domain", course=course)
    topic = Topic.objects.create(name="Test Topic", domain=domain)
    return department, course, domain, topic


def _create_question(topic, text, status=Question.Status.APPROVED, is_active=True):
    question = Question.objects.create(
        topic=topic,
        text=text,
        status=status,
        is_active=is_active,
    )
    for i, choice_text in enumerate(["A", "B", "C", "D"]):
        Choice.objects.create(
            question=question,
            text=choice_text,
            is_correct=(i == 0)
        )
    return question


def _create_student(department=None):
    return User.objects.create_user(
        username="adaptive_student",
        email="adaptive@test.com",
        password="testpass123",
        role="student",
        department=department,
    )


class AdaptiveQuizTests(TestCase):
    """Tests for the real adaptive topic quiz."""

    def setUp(self):
        self.client = APIClient()
        self.department, self.course, self.domain, self.topic = _create_test_hierarchy()
        self.student = _create_student(self.department)
        self.client.force_authenticate(user=self.student)

        for i in range(5):
            _create_question(self.topic, f"Quiz q{i}")

        self.path = generate_learning_path(self.student)
        # Force the path to the test topic.
        self.path.topic = self.topic.name
        self.path.current_step = "quiz"
        self.path.save()
        self.path.refresh_from_db()

    def test_quiz_returns_only_approved_active_questions(self):
        response = self.client.get("/api/adaptive-learning/quiz/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["questions"]), 5)
        for q in response.data["questions"]:
            db_q = Question.objects.get(id=q["id"])
            self.assertEqual(db_q.status, Question.Status.APPROVED)
            self.assertTrue(db_q.is_active)

    def test_quiz_rejects_frontend_provided_fake_scores(self):
        response = self.client.post(
            "/api/adaptive-learning/quiz/submit/",
            {"score": 95, "answers": []},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("scores", response.data["detail"].lower())

    def test_quiz_stores_real_answer_results(self):
        quiz_response = self.client.get("/api/adaptive-learning/quiz/")
        questions = quiz_response.data["questions"]
        answers = []
        for q in questions:
            correct_choice = Choice.objects.filter(
                question_id=q["id"],
                is_correct=True
            ).first()
            answers.append({
                "question_id": q["id"],
                "selected_choice_id": correct_choice.id
            })

        response = self.client.post(
            "/api/adaptive-learning/quiz/submit/",
            {"answers": answers},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["correct_count"], 5)
        self.assertEqual(response.data["total_questions"], 5)

        # Verify an attempt and details were stored.
        attempt = ExamAttempt.objects.get(id=response.data["attempt_id"])
        self.assertEqual(attempt.details.count(), 5)
        self.assertTrue(
            StudentTopicPerformance.objects.filter(
                student=self.student,
                topic=self.topic
            ).exists()
        )

    def test_quiz_only_accepts_answers_for_current_path_topic(self):
        other_topic = Topic.objects.create(
            name="Other Topic",
            domain=self.domain
        )
        other_q = _create_question(other_topic, "Other question")
        response = self.client.post(
            "/api/adaptive-learning/quiz/submit/",
            {"answers": [{"question_id": other_q.id, "selected_choice_id": other_q.choices.first().id}]},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdaptiveMiniMockTests(TestCase):
    """Tests for the real adaptive mini mock flow."""

    def setUp(self):
        self.client = APIClient()
        self.department, self.course, self.domain, self.topic = _create_test_hierarchy()
        self.student = _create_student(self.department)
        self.client.force_authenticate(user=self.student)

        for i in range(5):
            _create_question(self.topic, f"Mini q{i}")

        self.path = generate_learning_path(self.student)
        self.path.topic = self.topic.name
        self.path.current_step = "mini_mock"
        self.path.save()
        LearningStep.objects.filter(learning_path=self.path).update(completed=True)
        LearningStep.objects.filter(learning_path=self.path, step_type="mini_mock").update(completed=False)

    def test_mini_mock_complete_requires_submitted_attempt(self):
        response = self.client.post("/api/adaptive-learning/mini-mock/complete/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("submitted mini mock", response.data["detail"].lower())

    def test_mini_mock_complete_after_real_submission(self):
        # Generate a real mini mock via the existing endpoint.
        response = self.client.post(
            "/api/exit-exams/generate-mock-exam/",
            {"topic": self.topic.name, "total_questions": 5},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_exam_id = response.data["mock_exam"]["id"]

        questions = response.data["mock_exam"]["mock_questions"]
        answers = []
        for mq in questions:
            q = Question.objects.get(id=mq["question"]["id"])
            correct_choice = q.choices.filter(is_correct=True).first()
            answers.append({
                "question_id": q.id,
                "selected_choice_id": correct_choice.id
            })

        submit_response = self.client.post(
            "/api/exit-exams/submit-mock-exam/",
            {"mock_exam_id": mock_exam_id, "answers": answers},
            format="json"
        )
        self.assertEqual(submit_response.status_code, status.HTTP_200_OK)

        complete_response = self.client.post("/api/adaptive-learning/mini-mock/complete/")
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        self.assertTrue(complete_response.data["unlocked"])

        self.path.refresh_from_db()
        self.assertTrue(
            self.path.steps.filter(step_type="mini_mock", completed=True).exists()
        )


class WeakTopicPracticeTests(TestCase):
    """Tests for the weak-topic practice endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.department, self.course, self.domain, self.topic = _create_test_hierarchy()
        self.student = _create_student(self.department)
        self.client.force_authenticate(user=self.student)

        for i in range(5):
            _create_question(self.topic, f"Weak q{i}")

        # Create a low-accuracy performance record.
        StudentTopicPerformance.objects.create(
            student=self.student,
            domain=self.domain,
            topic=self.topic,
            correct_attempts=1,
            wrong_attempts=4,
            total_attempts=5,
        )

    def test_weak_topic_practice_uses_selected_topic(self):
        response = self.client.post(
            "/api/exit-exams/generate-mock-exam/",
            {"topic_id": self.topic.id, "total_questions": 5},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["mode"], "topic")
        self.assertEqual(response.data["mock_exam"]["total_questions"], 5)
        for mq in response.data["mock_exam"]["mock_questions"]:
            q = Question.objects.get(id=mq["question"]["id"])
            self.assertEqual(q.topic_id, self.topic.id)


class AdaptiveQuizDoesNotExposeCorrectAnswersTests(TestCase):
    """Ensure the quiz API never exposes the correct choice."""

    def setUp(self):
        self.client = APIClient()
        self.department, self.course, self.domain, self.topic = _create_test_hierarchy()
        self.student = _create_student(self.department)
        self.client.force_authenticate(user=self.student)

        for i in range(5):
            _create_question(self.topic, f"Quiz q{i}")
        path = generate_learning_path(self.student)
        path.topic = self.topic.name
        path.current_step = "quiz"
        path.save()

    def test_quiz_questions_hide_correct_flags(self):
        response = self.client.get("/api/adaptive-learning/quiz/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for q in response.data["questions"]:
            for choice in q["choices"]:
                self.assertNotIn("is_correct", choice)
