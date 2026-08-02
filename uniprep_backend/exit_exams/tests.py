"""
Tests for question selection consolidation and approved-only enforcement.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from .models import (
    Department,
    Course,
    Domain,
    Topic,
    Question,
    Choice,
    MockExam,
    ExamAttempt,
    AttemptDetail,
    ExamBlueprint,
    ExamBlueprintTopicRule,
    ExamBlueprintDomainRule,
)
from .services.question_selector import (
    select_questions_for_topic,
    select_questions_for_domain,
    select_questions_for_course,
    select_questions_for_blueprint,
    rank_questions_for_student,
)

User = get_user_model()


def _create_test_hierarchy():
    """Create a standard department/course/domain/topic tree."""
    department = Department.objects.create(name="Test Department", code="TSTD")
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
        username="test_student",
        email="student@test.com",
        password="testpass123",
        role="student",
        department=department,
    )


class QuestionSelectorPriorityTests(TestCase):
    """Tests for the consolidated question_selector service."""

    def setUp(self):
        self.department, self.course, self.domain, self.topic = _create_test_hierarchy()
        self.student = _create_student(self.department)

        self.q_unseen = _create_question(self.topic, "Unseen question")
        self.q_wrong = _create_question(self.topic, "Wrong question")
        self.q_correct = _create_question(self.topic, "Correct question")

        # Create a mock exam + attempt + details so q_wrong is "previously incorrect"
        # and q_correct is "previously correct".
        mock_exam = MockExam.objects.create(
            student=self.student,
            course=self.course,
            title="Past Mock",
            exam_number=1,
            total_questions=2,
        )
        attempt = ExamAttempt.objects.create(
            mock_exam=mock_exam,
            student=self.student,
            status=ExamAttempt.Status.SUBMITTED
        )
        AttemptDetail.objects.create(
            attempt=attempt,
            question=self.q_wrong,
            selected_choice=self.q_wrong.choices.first(),
            is_correct=False
        )
        correct_choice = self.q_correct.choices.filter(is_correct=True).first()
        AttemptDetail.objects.create(
            attempt=attempt,
            question=self.q_correct,
            selected_choice=correct_choice,
            is_correct=True
        )

    def test_unseen_means_never_submitted(self):
        """Unseen = no AttemptDetail record, regardless of MockExam inclusion."""
        # Add q_unseen to a mock exam but do not create an AttemptDetail.
        mock_exam = MockExam.objects.create(
            student=self.student,
            course=self.course,
            title="Mock with unseen",
            exam_number=2,
            total_questions=1,
        )
        from .models import MockExamQuestion
        MockExamQuestion.objects.create(
            mock_exam=mock_exam,
            question=self.q_unseen,
            order=1
        )

        ranked = rank_questions_for_student(
            self.student,
            Question.objects.filter(topic=self.topic)
        )
        ids = [q.id for q in ranked]

        self.assertEqual(ids[0], self.q_unseen.id)
        self.assertIn(self.q_wrong.id, ids[1:2])
        self.assertEqual(ids[2], self.q_correct.id)

    def test_previously_incorrect_gets_priority_two(self):
        """Previously incorrect questions are selected before correctly answered ones."""
        ranked = rank_questions_for_student(
            self.student,
            Question.objects.filter(topic=self.topic)
        )
        ids = [q.id for q in ranked]

        self.assertEqual(ids[0], self.q_unseen.id)
        self.assertEqual(ids[1], self.q_wrong.id)
        self.assertEqual(ids[2], self.q_correct.id)

    def test_select_questions_for_topic_returns_only_approved_active(self):
        _create_question(self.topic, "Draft", status=Question.Status.DRAFT)
        _create_question(self.topic, "Submitted", status=Question.Status.SUBMITTED)
        _create_question(self.topic, "Rejected", status=Question.Status.REJECTED)
        _create_question(self.topic, "Inactive", is_active=False)

        selected = select_questions_for_topic(self.student, self.topic, count=3)
        self.assertEqual(len(selected), 3)
        for q in selected:
            self.assertEqual(q.status, Question.Status.APPROVED)
            self.assertTrue(q.is_active)

    def test_select_questions_for_topic_raises_when_insufficient(self):
        Question.objects.filter(topic=self.topic).delete()
        _create_question(self.topic, "Only approved")
        with self.assertRaises(ValueError) as ctx:
            select_questions_for_topic(self.student, self.topic, count=5)
        self.assertIn("Not enough approved questions", str(ctx.exception))

    def test_select_questions_for_domain_returns_only_approved_active(self):
        _create_question(self.topic, "Draft", status=Question.Status.DRAFT)
        selected = select_questions_for_domain(self.student, self.domain, count=3)
        self.assertEqual(len(selected), 3)
        for q in selected:
            self.assertEqual(q.status, Question.Status.APPROVED)
            self.assertTrue(q.is_active)

    def test_select_questions_for_course_returns_only_approved_active(self):
        _create_question(self.topic, "Draft", status=Question.Status.DRAFT)
        selected = select_questions_for_course(self.student, self.course, total_questions=3)
        self.assertEqual(len(selected), 3)
        for q in selected:
            self.assertEqual(q.status, Question.Status.APPROVED)
            self.assertTrue(q.is_active)


class BlueprintSelectorTests(TestCase):
    """Regression tests for blueprint mock generation after consolidation."""

    def setUp(self):
        self.department, self.course, self.domain, self.topic = _create_test_hierarchy()
        self.student = _create_student(self.department)
        self.blueprint = ExamBlueprint.objects.create(
            course=self.course,
            title="Test Blueprint",
            total_questions=3,
            duration_minutes=60
        )
        ExamBlueprintTopicRule.objects.create(
            blueprint=self.blueprint,
            topic=self.topic,
            question_count=3
        )
        for i in range(3):
            _create_question(self.topic, f"Blueprint q{i}")

    def test_blueprint_generation_returns_correct_count(self):
        selected, report, warnings = select_questions_for_blueprint(
            self.student, self.blueprint
        )
        self.assertEqual(len(selected), 3)
        self.assertEqual(len(set(q.id for q in selected)), 3)
        self.assertEqual(report[0]["selected_total"], 3)
        self.assertFalse(warnings)

    def test_blueprint_generation_uses_only_approved_active(self):
        _create_question(self.topic, "Draft", status=Question.Status.DRAFT)
        selected, _, _ = select_questions_for_blueprint(
            self.student, self.blueprint
        )
        for q in selected:
            self.assertEqual(q.status, Question.Status.APPROVED)
            self.assertTrue(q.is_active)


class GenerateMockExamApprovedOnlyTests(TestCase):
    """API tests ensuring generate-mock-exam never returns unapproved questions."""

    def setUp(self):
        self.client = APIClient()
        self.department, self.course, self.domain, self.topic = _create_test_hierarchy()
        self.student = _create_student(self.department)
        self.client.force_authenticate(user=self.student)

    def _generate_topic_mock(self):
        return self.client.post(
            "/api/exit-exams/generate-mock-exam/",
            {"topic_id": self.topic.id, "total_questions": 5}
        )

    def test_topic_mode_returns_only_approved_active(self):
        for i in range(5):
            _create_question(self.topic, f"Approved {i}")
        response = self._generate_topic_mock()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for mq in response.data["mock_exam"]["mock_questions"]:
            q = Question.objects.get(id=mq["question"]["id"])
            self.assertEqual(q.status, Question.Status.APPROVED)
            self.assertTrue(q.is_active)

    def test_topic_mode_errors_when_only_draft_questions(self):
        _create_question(self.topic, "Draft", status=Question.Status.DRAFT)
        response = self._generate_topic_mock()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("approved questions", response.data["detail"])

    def test_topic_mode_errors_when_only_submitted_questions(self):
        _create_question(self.topic, "Submitted", status=Question.Status.SUBMITTED)
        response = self._generate_topic_mock()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("approved questions", response.data["detail"])

    def test_topic_mode_errors_when_only_rejected_questions(self):
        _create_question(self.topic, "Rejected", status=Question.Status.REJECTED)
        response = self._generate_topic_mock()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("approved questions", response.data["detail"])

    def test_topic_mode_errors_when_only_inactive_questions(self):
        _create_question(self.topic, "Inactive", is_active=False)
        response = self._generate_topic_mock()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("approved questions", response.data["detail"])

    def test_course_mode_returns_only_approved_active(self):
        for i in range(5):
            _create_question(self.topic, f"Approved {i}")
        response = self.client.post(
            "/api/exit-exams/generate-mock-exam/",
            {"course_id": self.course.id, "total_questions": 5}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for mq in response.data["mock_exam"]["mock_questions"]:
            q = Question.objects.get(id=mq["question"]["id"])
            self.assertEqual(q.status, Question.Status.APPROVED)
            self.assertTrue(q.is_active)

    def test_blueprint_mode_returns_only_approved_active(self):
        blueprint = ExamBlueprint.objects.create(
            course=self.course,
            title="Blueprint",
            total_questions=2,
            duration_minutes=30
        )
        ExamBlueprintTopicRule.objects.create(
            blueprint=blueprint,
            topic=self.topic,
            question_count=2
        )
        for i in range(2):
            _create_question(self.topic, f"Approved {i}")
        response = self.client.post(
            "/api/exit-exams/generate-mock-exam/",
            {"blueprint_id": blueprint.id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for mq in response.data["mock_exam"]["mock_questions"]:
            q = Question.objects.get(id=mq["question"]["id"])
            self.assertEqual(q.status, Question.Status.APPROVED)
            self.assertTrue(q.is_active)


class SubmitMockExamUpdatesTests(TestCase):
    """Tests that real mini mock submission creates records and updates readiness."""

    def setUp(self):
        self.client = APIClient()
        self.department, self.course, self.domain, self.topic = _create_test_hierarchy()
        self.student = _create_student(self.department)
        self.client.force_authenticate(user=self.student)

        self.questions = []
        for i in range(5):
            q = _create_question(self.topic, f"Mini mock q{i}")
            self.questions.append(q)

        response = self.client.post(
            "/api/exit-exams/generate-mock-exam/",
            {"topic_id": self.topic.id, "total_questions": 5}
        )
        self.mock_exam_id = response.data["mock_exam"]["id"]
        self.mock_question_ids = [
            mq["question"]["id"]
            for mq in response.data["mock_exam"]["mock_questions"]
        ]

    def test_mini_mock_generates_exactly_five_approved_active_questions(self):
        mock_exam = MockExam.objects.get(id=self.mock_exam_id)
        self.assertEqual(mock_exam.total_questions, 5)
        self.assertEqual(mock_exam.mock_questions.count(), 5)
        for mq in mock_exam.mock_questions.all():
            self.assertEqual(mq.question.status, Question.Status.APPROVED)
            self.assertTrue(mq.question.is_active)

    def test_mini_mock_submission_creates_attempt_and_details(self):
        answers = [
            {"question_id": qid, "selected_choice_id": Question.objects.get(id=qid).choices.first().id}
            for qid in self.mock_question_ids
        ]
        response = self.client.post(
            "/api/exit-exams/submit-mock-exam/",
            {"mock_exam_id": self.mock_exam_id, "answers": answers}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("attempt_id", response.data)
        self.assertEqual(response.data["total_questions"], 5)

        attempt = ExamAttempt.objects.get(id=response.data["attempt_id"])
        self.assertEqual(attempt.details.count(), 5)
        self.assertTrue(
            attempt.details.filter(question_id__in=self.mock_question_ids).exists()
        )

    def test_readiness_updates_after_mini_mock(self):
        from analytics.models import ReadinessScore
        answers = [
            {"question_id": qid, "selected_choice_id": Question.objects.get(id=qid).choices.filter(is_correct=True).first().id}
            for qid in self.mock_question_ids
        ]
        response = self.client.post(
            "/api/exit-exams/submit-mock-exam/",
            {"mock_exam_id": self.mock_exam_id, "answers": answers}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("readiness_score", response.data)

        readiness = ReadinessScore.objects.get(student=self.student, course=self.course)
        self.assertEqual(float(readiness.score), float(response.data["readiness_score"]))


class StudentPickerDepartmentScopingTests(TestCase):
    """Ensure course/topic/blueprint picker endpoints are scoped to the student's department."""

    def setUp(self):
        self.client = APIClient()
        self.cs_department, self.cs_course, self.cs_domain, self.cs_topic = _create_test_hierarchy()
        self.cs_course.name = "CS Scoped Course"
        self.cs_course.save()

        self.ba_department = Department.objects.create(name="BA Scoped Department", code="BASD")
        self.ba_course = Course.objects.create(name="BA Scoped Course", department=self.ba_department)
        self.ba_domain = Domain.objects.create(name="BA Scoped Domain", course=self.ba_course)
        self.ba_topic = Topic.objects.create(name="BA Scoped Topic", domain=self.ba_domain)

        self.cs_blueprint = ExamBlueprint.objects.create(
            course=self.cs_course,
            title="CS Scoped Blueprint",
            total_questions=1,
            duration_minutes=30,
            is_active=True,
        )
        ExamBlueprintTopicRule.objects.create(
            blueprint=self.cs_blueprint,
            topic=self.cs_topic,
            question_count=1,
        )

        self.ba_blueprint = ExamBlueprint.objects.create(
            course=self.ba_course,
            title="BA Scoped Blueprint",
            total_questions=1,
            duration_minutes=30,
            is_active=True,
        )
        ExamBlueprintTopicRule.objects.create(
            blueprint=self.ba_blueprint,
            topic=self.ba_topic,
            question_count=1,
        )

        self.cs_student = _create_student(self.cs_department)
        self.ba_student = User.objects.create_user(
            username="ba_scoped_student",
            email="ba_scoped@test.com",
            password="testpass123",
            role="student",
            department=self.ba_department,
        )

    def _ids(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return {item["id"] for item in response.data}

    def test_student_courses_scoped_to_department(self):
        self.client.force_authenticate(user=self.ba_student)
        ids = self._ids(self.client.get("/api/exit-exams/courses/"))
        self.assertIn(self.ba_course.id, ids)
        self.assertNotIn(self.cs_course.id, ids)

        self.client.force_authenticate(user=self.cs_student)
        ids = self._ids(self.client.get("/api/exit-exams/courses/"))
        self.assertIn(self.cs_course.id, ids)
        self.assertNotIn(self.ba_course.id, ids)

    def test_student_domains_scoped_to_department(self):
        self.client.force_authenticate(user=self.ba_student)
        ids = self._ids(self.client.get("/api/exit-exams/domains/"))
        self.assertIn(self.ba_domain.id, ids)
        self.assertNotIn(self.cs_domain.id, ids)

        self.client.force_authenticate(user=self.cs_student)
        ids = self._ids(self.client.get("/api/exit-exams/domains/"))
        self.assertIn(self.cs_domain.id, ids)
        self.assertNotIn(self.ba_domain.id, ids)

    def test_student_topics_scoped_to_department(self):
        self.client.force_authenticate(user=self.ba_student)
        ids = self._ids(self.client.get("/api/exit-exams/topics/"))
        self.assertIn(self.ba_topic.id, ids)
        self.assertNotIn(self.cs_topic.id, ids)

        self.client.force_authenticate(user=self.cs_student)
        ids = self._ids(self.client.get("/api/exit-exams/topics/"))
        self.assertIn(self.cs_topic.id, ids)
        self.assertNotIn(self.ba_topic.id, ids)

    def test_student_blueprints_scoped_to_department(self):
        self.client.force_authenticate(user=self.ba_student)
        ids = self._ids(self.client.get("/api/exit-exams/exam-blueprints/"))
        self.assertIn(self.ba_blueprint.id, ids)
        self.assertNotIn(self.cs_blueprint.id, ids)

        self.client.force_authenticate(user=self.cs_student)
        ids = self._ids(self.client.get("/api/exit-exams/exam-blueprints/"))
        self.assertIn(self.cs_blueprint.id, ids)
        self.assertNotIn(self.ba_blueprint.id, ids)
