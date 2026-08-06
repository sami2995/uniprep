from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        DEPARTMENT_HEAD = "department_head", "Department Head"
        SYSTEM_ADMIN = "system_admin", "System Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT
    )
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    verification = models.CharField(
        max_length=10,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_students",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    department = models.ForeignKey(
        "exit_exams.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )
    email = models.EmailField(unique=True)

    def is_student(self):
        return self.role == self.Role.STUDENT

    def is_teacher(self):
        return self.role == self.Role.TEACHER

    def is_department_head(self):
        return self.role == self.Role.DEPARTMENT_HEAD

    def is_system_admin(self):
        return self.role == self.Role.SYSTEM_ADMIN

    def is_admin_user(self):
        return (
            self.is_staff
            or self.role in {
                self.Role.DEPARTMENT_HEAD,
                self.Role.SYSTEM_ADMIN,
                "admin",
            }
        )


class StudentProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )
    student_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100, blank=True)
    program = models.CharField(max_length=100, blank=True)
    year_of_study = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.student_id}"
