from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

from .models import CustomUser
from .serializers import RegisterSerializer, UserSerializer
from exit_exams.models import Course, TeacherCourseAssignment


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