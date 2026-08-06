from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from exit_exams.models import Department, AuditLog, Course, Domain, Topic, Question, Choice

User = get_user_model()


class AdminCreateUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.system_admin = User.objects.create_user(
            username="sysadmin",
            email="sysadmin@example.com",
            password="adminpass123",
            role="system_admin",
        )
        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@example.com",
            password="teacherpass123",
            role="teacher",
        )
        self.department_head = User.objects.create_user(
            username="depthead",
            email="depthead@example.com",
            password="deptheadpass123",
            role="department_head",
        )
        self.student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="studentpass123",
            role="student",
        )
        self.department = Department.objects.create(name="Computer Science", code="CS")

    def test_system_admin_can_create_student_without_department(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "newstudent",
                "email": "newstudent@example.com",
                "password": "studentpass123",
                "role": "student",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "newstudent")
        self.assertEqual(response.data["role"], "student")
        self.assertIsNone(response.data["department_id"])

        user = User.objects.get(username="newstudent")
        self.assertEqual(user.role, "student")
        self.assertIsNone(user.department)
        self.assertTrue(hasattr(user, "student_profile"))

    def test_system_admin_can_create_student_with_department(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "newstudent2",
                "email": "newstudent2@example.com",
                "password": "studentpass123",
                "role": "student",
                "department_id": self.department.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["department_id"], self.department.id)

        user = User.objects.get(username="newstudent2")
        self.assertEqual(user.department_id, self.department.id)
        self.assertEqual(user.student_profile.department, self.department.name)

    def test_system_admin_can_create_teacher_with_department(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "newteacher",
                "email": "newteacher@example.com",
                "password": "teacherpass123",
                "role": "teacher",
                "department_id": self.department.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], "teacher")
        self.assertEqual(response.data["department_id"], self.department.id)

        user = User.objects.get(username="newteacher")
        self.assertEqual(user.role, "teacher")
        self.assertEqual(user.department_id, self.department.id)
        self.assertFalse(hasattr(user, "student_profile"))

    def test_system_admin_can_create_department_head_with_department(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "newdepthead",
                "email": "newdepthead@example.com",
                "password": "deptheadpass123",
                "role": "department_head",
                "department_id": self.department.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], "department_head")
        self.assertEqual(response.data["department_id"], self.department.id)

        user = User.objects.get(username="newdepthead")
        self.assertEqual(user.role, "department_head")
        self.assertEqual(user.department_id, self.department.id)

    def test_cannot_create_system_admin(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "newsysadmin",
                "email": "newsysadmin@example.com",
                "password": "adminpass123",
                "role": "system_admin",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data)
        self.assertFalse(User.objects.filter(username="newsysadmin").exists())

    def test_teacher_requires_department(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "newteacher",
                "email": "newteacher@example.com",
                "password": "teacherpass123",
                "role": "teacher",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department_id", response.data)
        self.assertFalse(User.objects.filter(username="newteacher").exists())

    def test_department_head_requires_department(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "newdepthead",
                "email": "newdepthead@example.com",
                "password": "deptheadpass123",
                "role": "department_head",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department_id", response.data)
        self.assertFalse(User.objects.filter(username="newdepthead").exists())

    def test_invalid_department_rejected(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "newteacher",
                "email": "newteacher@example.com",
                "password": "teacherpass123",
                "role": "teacher",
                "department_id": 9999,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department_id", response.data)
        self.assertEqual(
            response.data["department_id"],
            ["Selected department does not match any existing department."],
        )

    def test_department_name_case_insensitive_resolution(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "newteacher",
                "email": "newteacher@example.com",
                "password": "teacherpass123",
                "role": "teacher",
                "department_id": "computer science",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["department_id"], self.department.id)

    def test_non_system_admin_forbidden(self):
        for user in [self.student, self.teacher, self.department_head]:
            self.client.force_authenticate(user=user)
            response = self.client.post(
                "/api/users/admin-create-user/",
                {
                    "username": "shouldfail",
                    "email": "shouldfail@example.com",
                    "password": "pass1234",
                    "role": "student",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertFalse(User.objects.filter(username="shouldfail").exists())

    def test_unauthenticated_rejected(self):
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "shouldfail",
                "email": "shouldfail@example.com",
                "password": "pass1234",
                "role": "student",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_username_rejected(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": self.student.username,
                "email": "unique@example.com",
                "password": "pass1234",
                "role": "student",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_duplicate_email_rejected(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "uniqueuser",
                "email": self.student.email,
                "password": "pass1234",
                "role": "student",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_new_user_can_login(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "logintest",
                "email": "logintest@example.com",
                "password": "loginpass123",
                "role": "teacher",
                "department_id": self.department.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=None)
        token_response = self.client.post(
            "/api/token/",
            {"username": "logintest", "password": "loginpass123"},
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", token_response.data)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}"
        )
        me_response = self.client.get("/api/users/me/")
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["role"], "teacher")
        self.assertEqual(me_response.data["department"], self.department.id)

    def test_creates_audit_log(self):
        self.client.force_authenticate(user=self.system_admin)
        response = self.client.post(
            "/api/users/admin-create-user/",
            {
                "username": "audittest",
                "email": "audittest@example.com",
                "password": "pass1234",
                "role": "student",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_id = response.data["id"]
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.CREATED,
                entity_type="user",
                entity_id=user_id,
            ).exists()
        )


class StudentVerificationAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.department = Department.objects.create(name="Verification Department", code="VRFY")
        course = Course.objects.create(name="Verification Course", department=self.department)
        domain = Domain.objects.create(name="Verification Domain", course=course)
        topic = Topic.objects.create(name="Verification Topic", domain=domain)
        question = Question.objects.create(
            topic=topic,
            text="Institution question",
            status=Question.Status.APPROVED,
            is_active=True,
        )
        for index, text in enumerate(["A", "B", "C", "D"]):
            Choice.objects.create(question=question, text=text, is_correct=index == 0)
        self.course = course
        self.admin = User.objects.create_user(
            username="verification_admin",
            email="verification_admin@example.com",
            password="adminpass123",
            role="system_admin",
            verification="verified",
        )

    def test_registration_is_pending_and_exam_content_is_blocked(self):
        registration = self.client.post(
            "/api/users/register/",
            {
                "username": "pending_student",
                "email": "pending_student@example.com",
                "password": "studentpass123",
                "password2": "studentpass123",
                "department": self.department.name,
            },
            format="json",
        )
        self.assertEqual(registration.status_code, status.HTTP_201_CREATED)
        student = User.objects.get(username="pending_student")
        self.assertEqual(student.verification, "pending")

        self.client.force_authenticate(user=student)
        questions = self.client.get("/api/exit-exams/questions/")
        mock = self.client.post(
            "/api/exit-exams/generate-mock-exam/",
            {"course_id": self.course.id, "total_questions": 1},
            format="json",
        )
        self.assertEqual(questions.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(mock.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(questions.data["verification_status"], "pending")

    def test_registration_requires_department(self):
        response = self.client.post(
            "/api/users/register/",
            {
                "username": "missing_department",
                "email": "missing_department@example.com",
                "password": "studentpass123",
                "password2": "studentpass123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department", response.data)
        self.assertFalse(User.objects.filter(username="missing_department").exists())

    def test_verification_rejects_student_without_department(self):
        student = User.objects.create_user(
            username="null_department_student",
            email="null_department@example.com",
            password="studentpass123",
            role="student",
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/admin/users/{student.id}/verify/",
            {"action": "verify"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("no department", response.data["error"])
        student.refresh_from_db()
        self.assertEqual(student.verification, "pending")


    def test_system_admin_can_verify_student(self):
        student = User.objects.create_user(
            username="queue_student",
            email="queue_student@example.com",
            password="studentpass123",
            role="student",
            department=self.department,
        )
        self.client.force_authenticate(user=self.admin)
        queue = self.client.get("/api/admin/users/pending-verification/")
        self.assertEqual(queue.status_code, status.HTTP_200_OK)
        self.assertIn(student.id, {item["id"] for item in queue.data})

        response = self.client.post(
            f"/api/admin/users/{student.id}/verify/",
            {"action": "verify"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        student.refresh_from_db()
        self.assertEqual(student.verification, "verified")
        self.assertEqual(student.verified_by_id, self.admin.id)
