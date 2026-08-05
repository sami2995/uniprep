from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

from .models import CustomUser, StudentProfile
from .serializers import RegisterSerializer, UserSerializer
from exit_exams.models import Course, TeacherCourseAssignment, TeacherTopicAssignment, Department, AuditLog
from exit_exams.permissions import IsSystemAdminOnly


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    if request.method == "PATCH":
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

    serializer = UserSerializer(request.user)
    user_data = serializer.data

    if request.user.role == CustomUser.Role.TEACHER:
        user_data["assigned_courses"] = list(
            TeacherCourseAssignment.objects.filter(
                teacher=request.user
            ).values_list("course__name", flat=True)
        )
        user_data["assigned_topics"] = list(
            TeacherTopicAssignment.objects.filter(
                teacher=request.user, active=True
            ).values_list("topic__name", flat=True)
        )
        user_data["questions_authored"] = request.user.created_questions.count()
    elif request.user.role == CustomUser.Role.DEPARTMENT_HEAD:
        user_data["courses_managed"] = Course.objects.filter(
            department=request.user.department
        ).count()
    elif request.user.role in {
        CustomUser.Role.SYSTEM_ADMIN,
        "admin",
    }:
        user_data["total_students"] = CustomUser.objects.filter(
            role=CustomUser.Role.STUDENT
        ).count()
        user_data["total_teachers"] = CustomUser.objects.filter(
            role=CustomUser.Role.TEACHER
        ).count()

    return Response(user_data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    current_password = request.data.get("current_password")
    new_password = request.data.get("new_password")
    confirm_password = request.data.get("confirm_password")

    if not current_password or not new_password or not confirm_password:
        return Response(
            {"detail": "Current password, new password, and confirmation are required."},
            status=400,
        )

    if not request.user.check_password(current_password):
        return Response(
            {"current_password": ["Current password is incorrect."]},
            status=400,
        )

    if new_password != confirm_password:
        return Response(
            {"new_password": ["New passwords do not match."]},
            status=400,
        )

    try:
        validate_password(new_password, request.user)
    except DjangoValidationError as error:
        return Response({"new_password": error.messages}, status=400)

    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    return Response({"detail": "Password changed successfully."})


def _resolve_department(value):
    """Resolve a department identifier to a Department instance.

    Supports both primary-key lookup and case-insensitive name matching to
    match the resolution pattern used by RegisterSerializer.
    """
    if not value:
        return None
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        try:
            return Department.objects.get(pk=int(value))
        except Department.DoesNotExist:
            pass
    return Department.objects.filter(name__iexact=value).first()


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, IsSystemAdminOnly])
def admin_create_user(request):
    data = request.data
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")
    department_id = data.get("department_id")

    errors = {}
    if not username:
        errors["username"] = ["This field is required."]
    if not email:
        errors["email"] = ["This field is required."]
    if not password:
        errors["password"] = ["This field is required."]
    elif len(password) < 6:
        errors["password"] = ["Password must be at least 6 characters."]
    if not role:
        errors["role"] = ["This field is required."]

    allowed_roles = {
        CustomUser.Role.STUDENT,
        CustomUser.Role.TEACHER,
        CustomUser.Role.DEPARTMENT_HEAD,
    }
    if role and role not in allowed_roles:
        errors["role"] = [
            "Invalid role. Allowed roles: student, teacher, department_head."
        ]

    department = None
    if role in {CustomUser.Role.TEACHER, CustomUser.Role.DEPARTMENT_HEAD}:
        if not department_id:
            errors["department_id"] = ["Department is required for this role."]
        else:
            department = _resolve_department(department_id)
            if not department:
                errors["department_id"] = [
                    "Selected department does not match any existing department."
                ]
    elif department_id:
        department = _resolve_department(department_id)
        if not department:
            errors["department_id"] = [
                "Selected department does not match any existing department."
            ]

    if username and CustomUser.objects.filter(username=username).exists():
        errors["username"] = ["A user with that username already exists."]
    if email and CustomUser.objects.filter(email=email).exists():
        errors["email"] = ["A user with that email already exists."]

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    user = CustomUser.objects.create_user(
        username=username,
        email=email,
        password=password,
        role=role,
        department=department,
    )

    if role == CustomUser.Role.STUDENT:
        StudentProfile.objects.create(
            user=user,
            student_id=user.username,
            department=department.name if department else "",
            program="",
            year_of_study=None,
        )

    AuditLog.objects.create(
        user=request.user,
        action=AuditLog.Action.CREATED,
        entity_type="user",
        entity_id=user.id,
        new_value={
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "department_id": user.department_id,
        },
        description=(
            f"System admin {request.user.username} created user "
            f"{user.username} with role {user.role}."
        ),
    )

    return Response(
        {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "department_id": user.department_id,
        },
        status=status.HTTP_201_CREATED,
    )