"""
Tests for question approval workflow security.
Validates that system admins cannot approve/reject questions through any path.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from .models import (
    Question,
    Department,
    Course,
    Domain,
    Topic,
    ExtractedQuestion,
    ExamPdfImport,
    TeacherCourseAssignment,
)

User = get_user_model()


class QuestionApprovalWorkflowSecurityTests(TestCase):
    """
    Tests for the question approval workflow to ensure system admins
    cannot bypass the approval process.
    """

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create department
        self.department = Department.objects.create(name="Engineering")

        # Create course
        self.course = Course.objects.create(
            name="Introduction to CS",
            department=self.department,
        )

        # Create domain
        self.domain = Domain.objects.create(
            name="Algorithms",
            course=self.course,
        )

        # Create topic
        self.topic = Topic.objects.create(
            name="Sorting",
            domain=self.domain,
        )

        # Create test users
        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@example.com",
            password="testpass123",
            role="teacher",
        )

        self.department_head = User.objects.create_user(
            username="dept_head",
            email="dept_head@example.com",
            password="testpass123",
            role="department_head",
            department=self.department,
        )

        self.system_admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass123",
            role="system_admin",
        )

        # Create exam pdf import
        self.exam_import = ExamPdfImport.objects.create(
            course=self.course,
            title="Test PDF Import",
            uploaded_by=self.system_admin,
            status=ExamPdfImport.Status.UPLOADED,
        )

        # Create a draft question
        self.question = Question.objects.create(
            topic=self.topic,
            text="What is the time complexity of quicksort?",
            created_by=self.teacher,
            status=Question.Status.DRAFT,
            is_active=False,
        )

        # Create a submitted question
        self.submitted_question = Question.objects.create(
            topic=self.topic,
            text="What is the space complexity of merge sort?",
            created_by=self.teacher,
            status=Question.Status.SUBMITTED,
            submitted_at="2025-01-01T00:00:00Z",
            is_active=False,
        )

    def test_system_admin_cannot_approve_question(self):
        """System admin should be denied approval of submitted questions."""
        self.client.force_authenticate(user=self.system_admin)

        response = self.client.post(
            f"/api/exit-exams/questions/{self.submitted_question.id}/approve/"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("System admins cannot", response.data["detail"])

        # Verify question status did not change
        self.submitted_question.refresh_from_db()
        self.assertEqual(self.submitted_question.status, Question.Status.SUBMITTED)

    def test_system_admin_cannot_reject_question(self):
        """System admin should be denied rejection of submitted questions."""
        self.client.force_authenticate(user=self.system_admin)

        response = self.client.post(
            f"/api/exit-exams/questions/{self.submitted_question.id}/reject/",
            {"rejection_reason": "Does not meet quality standards"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("System admins cannot", response.data["detail"])

        # Verify question status did not change
        self.submitted_question.refresh_from_db()
        self.assertEqual(self.submitted_question.status, Question.Status.SUBMITTED)

    def test_department_head_can_approve_question(self):
        """Department head should be able to approve submitted questions in their department."""
        self.client.force_authenticate(user=self.department_head)

        response = self.client.post(
            f"/api/exit-exams/questions/{self.submitted_question.id}/approve/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify question status changed
        self.submitted_question.refresh_from_db()
        self.assertEqual(self.submitted_question.status, Question.Status.APPROVED)
        self.assertEqual(self.submitted_question.reviewed_by, self.department_head)
        self.assertTrue(self.submitted_question.is_active)

    def test_department_head_can_reject_question(self):
        """Department head should be able to reject submitted questions in their department."""
        self.client.force_authenticate(user=self.department_head)

        response = self.client.post(
            f"/api/exit-exams/questions/{self.submitted_question.id}/reject/",
            {"rejection_reason": "Poorly worded question"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify question status changed
        self.submitted_question.refresh_from_db()
        self.assertEqual(self.submitted_question.status, Question.Status.REJECTED)
        self.assertEqual(self.submitted_question.reviewed_by, self.department_head)
        self.assertEqual(self.submitted_question.rejection_reason, "Poorly worded question")
        self.assertFalse(self.submitted_question.is_active)

    def test_system_admin_cannot_approve_extracted_question(self):
        """System admin should be denied approval of extracted questions from PDF imports."""
        extracted = ExtractedQuestion.objects.create(
            exam_import=self.exam_import,
            question_text="What is a binary search tree?",
            option_a="A tree structure",
            option_b="A search algorithm",
            option_c="A sorting method",
            option_d="A data structure",
            correct_answer="D",
            topic=self.topic,
            status=ExtractedQuestion.Status.DRAFT,
        )

        self.client.force_authenticate(user=self.system_admin)

        response = self.client.post(
            f"/api/exit-exams/extracted-questions/{extracted.id}/approve/"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("System admins cannot", response.data["detail"])

        # Verify extracted question status did not change
        extracted.refresh_from_db()
        self.assertEqual(extracted.status, ExtractedQuestion.Status.DRAFT)

    def test_system_admin_cannot_reject_extracted_question(self):
        """System admin should be denied rejection of extracted questions from PDF imports."""
        extracted = ExtractedQuestion.objects.create(
            exam_import=self.exam_import,
            question_text="What is a linked list?",
            option_a="A list of links",
            option_b="A data structure",
            option_c="A sorting algorithm",
            option_d="A search method",
            correct_answer="B",
            topic=self.topic,
            status=ExtractedQuestion.Status.DRAFT,
        )

        self.client.force_authenticate(user=self.system_admin)

        response = self.client.post(
            f"/api/exit-exams/extracted-questions/{extracted.id}/reject/"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("System admins cannot", response.data["detail"])

        # Verify extracted question status did not change
        extracted.refresh_from_db()
        self.assertEqual(extracted.status, ExtractedQuestion.Status.DRAFT)

    def test_department_head_can_approve_extracted_question(self):
        """Department head should be able to approve extracted questions in their department."""
        extracted = ExtractedQuestion.objects.create(
            exam_import=self.exam_import,
            question_text="What is a graph?",
            option_a="A visualization",
            option_b="A data structure",
            option_c="A sorting method",
            option_d="A search algorithm",
            correct_answer="B",
            topic=self.topic,
            status=ExtractedQuestion.Status.SUBMITTED,
        )

        self.client.force_authenticate(user=self.department_head)

        response = self.client.post(
            f"/api/exit-exams/extracted-questions/{extracted.id}/approve/"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify extracted question and corresponding Question were created
        extracted.refresh_from_db()
        self.assertEqual(extracted.status, ExtractedQuestion.Status.APPROVED)
        self.assertIsNotNone(extracted.approved_question)
        self.assertEqual(
            extracted.approved_question.status, Question.Status.APPROVED
        )

    def test_department_head_can_reject_extracted_question(self):
        """Department head should be able to reject extracted questions in their department."""
        extracted = ExtractedQuestion.objects.create(
            exam_import=self.exam_import,
            question_text="What is a stack?",
            option_a="A data structure",
            option_b="A sorting method",
            option_c="A search algorithm",
            option_d="A visualization",
            correct_answer="A",
            topic=self.topic,
            status=ExtractedQuestion.Status.SUBMITTED,
        )

        self.client.force_authenticate(user=self.department_head)

        response = self.client.post(
            f"/api/exit-exams/extracted-questions/{extracted.id}/reject/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify extracted question status changed
        extracted.refresh_from_db()
        self.assertEqual(extracted.status, ExtractedQuestion.Status.REJECTED)


class DepartmentHeadScopingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Departments
        self.dept_cs = Department.objects.create(name="Computer Science CS", code="CS_DH")
        self.dept_ee = Department.objects.create(name="Electrical Eng EE", code="EE_DH")

        # Department Heads
        self.dh_cs = User.objects.create_user(
            username="dh_cs_user",
            email="dh_cs@example.com",
            password="password123",
            role="department_head",
            department=self.dept_cs,
        )
        self.dh_ee = User.objects.create_user(
            username="dh_ee_user",
            email="dh_ee@example.com",
            password="password123",
            role="department_head",
            department=self.dept_ee,
        )

        # System Admin
        self.sys_admin = User.objects.create_user(
            username="sys_admin_dh_test",
            email="sysadmin@example.com",
            password="password123",
            role="system_admin",
        )

        # Teachers
        self.teacher_cs = User.objects.create_user(
            username="teacher_cs_user",
            email="t_cs@example.com",
            password="password123",
            role="teacher",
            department=self.dept_cs,
        )
        self.teacher_ee = User.objects.create_user(
            username="teacher_ee_user",
            email="t_ee@example.com",
            password="password123",
            role="teacher",
            department=self.dept_ee,
        )

        # Courses
        self.course_cs = Course.objects.create(name="CS 101", department=self.dept_cs)
        self.course_ee = Course.objects.create(name="EE 101", department=self.dept_ee)

        # Domains & Topics
        self.domain_cs = Domain.objects.create(name="CS Domain", course=self.course_cs)
        self.domain_ee = Domain.objects.create(name="EE Domain", course=self.course_ee)

        self.topic_cs = Topic.objects.create(name="CS Topic", domain=self.domain_cs)
        self.topic_ee = Topic.objects.create(name="EE Topic", domain=self.domain_ee)

        # Assignment
        self.assignment_ee = TeacherCourseAssignment.objects.create(
            teacher=self.teacher_ee,
            course=self.course_ee
        )

    def test_department_head_course_scoping(self):
        """Dept Head CS should see only CS course and fail to update or delete EE course."""
        self.client.force_authenticate(user=self.dh_cs)

        # List courses
        response = self.client.get("/api/exit-exams/courses/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_ids = [c["id"] for c in response.data]
        self.assertIn(self.course_cs.id, course_ids)
        self.assertNotIn(self.course_ee.id, course_ids)

        # Try updating EE course (cross-dept)
        response = self.client.patch(
            f"/api/exit-exams/courses/{self.course_ee.id}/",
            {"name": "Hacked EE Course"}
        )
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # Try creating course in EE department
        response = self.client.post(
            "/api/exit-exams/courses/",
            {"name": "New EE Course", "department": self.dept_ee.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_department_head_assignment_scoping(self):
        """Dept Head CS should not see or alter EE teacher assignments."""
        teacher_unassigned = User.objects.create_user(
            username="t_unassigned",
            email="t_unassigned@example.com",
            password="password123",
            role="teacher",
            department=self.dept_ee,
        )
        self.client.force_authenticate(user=self.dh_cs)

        # List assignments
        response = self.client.get("/api/exit-exams/teacher-course-assignments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assignment_ids = [a["id"] for a in response.data]
        self.assertNotIn(self.assignment_ee.id, assignment_ids)

        # Try assigning EE teacher to EE course as CS Dept Head
        response = self.client.post(
            "/api/exit-exams/teacher-course-assignments/",
            {"teacher": teacher_unassigned.id, "course": self.course_ee.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try assigning CS teacher to EE course
        response = self.client.post(
            "/api/exit-exams/teacher-course-assignments/",
            {"teacher": self.teacher_cs.id, "course": self.course_ee.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_department_head_domain_and_topic_scoping(self):
        """Dept Head CS should not create or update EE domains or topics."""
        self.client.force_authenticate(user=self.dh_cs)

        # Create domain in EE course
        response = self.client.post(
            "/api/exit-exams/domains/",
            {"name": "Unallowed EE Domain", "course": self.course_ee.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Create topic in EE domain
        response = self.client.post(
            "/api/exit-exams/topics/",
            {"name": "Unallowed EE Topic", "domain": self.domain_ee.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_department_head_department_mutations_restricted(self):
        """Dept Head should not create or delete departments or update other departments."""
        self.client.force_authenticate(user=self.dh_cs)

        # Create department
        response = self.client.post(
            "/api/exit-exams/departments/",
            {"name": "Illegal Dept", "code": "ILL"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Delete department
        response = self.client.delete(f"/api/exit-exams/departments/{self.dept_ee.id}/")
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # Update another department
        response = self.client.patch(
            f"/api/exit-exams/departments/{self.dept_ee.id}/",
            {"name": "Modified EE Dept"}
        )
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_system_admin_global_access(self):
        """System Admin should have global access to create courses and assignments in any department."""
        self.client.force_authenticate(user=self.sys_admin)

        response = self.client.get("/api/exit-exams/courses/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        response = self.client.post(
            "/api/exit-exams/teacher-course-assignments/",
            {"teacher": self.teacher_cs.id, "course": self.course_cs.id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TeacherMCQChoiceWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.dept = Department.objects.create(name="Computer Science MCQ", code="CS_MCQ")
        self.teacher = User.objects.create_user(
            username="mcq_teacher",
            email="mcq_t@example.com",
            password="password123",
            role="teacher",
            department=self.dept,
        )
        self.course = Course.objects.create(name="CS 201 MCQ", department=self.dept)
        TeacherCourseAssignment.objects.create(teacher=self.teacher, course=self.course)

        self.domain = Domain.objects.create(name="Algo Domain", course=self.course)
        self.topic = Topic.objects.create(name="Sorting Topic", domain=self.domain)

    def test_teacher_nested_question_and_choices_creation(self):
        """Teacher can create a complete question with 4 choices in a single request."""
        self.client.force_authenticate(user=self.teacher)

        payload = {
            "topic": self.topic.id,
            "text": "What is the time complexity of QuickSort average case?",
            "bloom_level": "knowledge",
            "difficulty": "medium",
            "choices": [
                {"text": "O(N^2)", "is_correct": False},
                {"text": "O(N log N)", "is_correct": True},
                {"text": "O(N)", "is_correct": False},
                {"text": "O(1)", "is_correct": False},
            ],
        }

        response = self.client.post("/api/exit-exams/questions/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "draft")

        question_id = response.data["id"]
        question = Question.objects.get(id=question_id)
        self.assertEqual(question.choices.count(), 4)
        correct_choice = question.choices.get(is_correct=True)
        self.assertEqual(correct_choice.text, "O(N log N)")

    def test_teacher_nested_choices_validation_errors(self):
        """Validation fails if choices count != 4 or correct answers != 1."""
        self.client.force_authenticate(user=self.teacher)

        # Less than 4 choices
        payload_invalid_count = {
            "topic": self.topic.id,
            "text": "Invalid count question?",
            "choices": [
                {"text": "Option A", "is_correct": True},
                {"text": "Option B", "is_correct": False},
            ],
        }
        response = self.client.post("/api/exit-exams/questions/", payload_invalid_count, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # No correct answer
        payload_no_correct = {
            "topic": self.topic.id,
            "text": "No correct answer question?",
            "choices": [
                {"text": "A", "is_correct": False},
                {"text": "B", "is_correct": False},
                {"text": "C", "is_correct": False},
                {"text": "D", "is_correct": False},
            ],
        }
        response = self.client.post("/api/exit-exams/questions/", payload_no_correct, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_modify_choices_for_approved_questions(self):
        """Editing choices via ChoiceViewSet or QuestionViewSet is blocked for approved questions."""
        question = Question.objects.create(
            topic=self.topic,
            text="Approved Question Text?",
            created_by=self.teacher,
            status=Question.Status.APPROVED,
            is_active=True,
        )
        from exit_exams.models import Choice
        choice = Choice.objects.create(question=question, text="Original Choice", is_correct=True)

        self.client.force_authenticate(user=self.teacher)

        # Try editing choice via ChoiceViewSet
        response = self.client.patch(f"/api/exit-exams/choices/{choice.id}/", {"text": "Modified Choice"})
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # Try editing choices via QuestionViewSet
        response = self.client.patch(
            f"/api/exit-exams/questions/{question.id}/",
            {
                "choices": [
                    {"text": "Choice 1", "is_correct": True},
                    {"text": "Choice 2", "is_correct": False},
                    {"text": "Choice 3", "is_correct": False},
                    {"text": "Choice 4", "is_correct": False},
                ]
            },
            format="json"
        )
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_cannot_approve_or_reject_draft_extracted_questions(self):
        """Department head cannot approve or reject draft extracted questions (must be submitted)."""
        dept_head = User.objects.create_user(
            username="dh_extracted_test",
            email="dh_ext@example.com",
            password="password123",
            role="department_head",
            department=self.dept,
        )

        extracted_draft = ExtractedQuestion.objects.create(
            exam_import=ExamPdfImport.objects.create(
                course=self.course,
                title="Draft Exam Import",
                uploaded_by=self.teacher,
            ),
            question_text="Draft Extracted Question Text?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_answer="A",
            topic=self.topic,
            status=ExtractedQuestion.Status.DRAFT,
        )

        self.client.force_authenticate(user=dept_head)

        # Approve on draft must return HTTP 400
        approve_resp = self.client.post(f"/api/exit-exams/extracted-questions/{extracted_draft.id}/approve/")
        self.assertEqual(approve_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(approve_resp.data["detail"], "Only submitted extracted questions can be approved.")

        # Reject on draft must return HTTP 400
        reject_resp = self.client.post(f"/api/exit-exams/extracted-questions/{extracted_draft.id}/reject/")
        self.assertEqual(reject_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(reject_resp.data["detail"], "Only submitted extracted questions can be rejected.")


