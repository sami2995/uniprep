from rest_framework import serializers
from .models import CustomUser, StudentProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, min_length=6)

    student_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    department = serializers.CharField(write_only=True, required=False, allow_blank=True)
    program = serializers.CharField(write_only=True, required=False, allow_blank=True)
    year_of_study = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "password",
            "password2",
            "student_id",
            "department",
            "program",
            "year_of_study",
        ]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError(
                {"password": "Passwords do not match."}
            )
        return data

    def create(self, validated_data):
        validated_data.pop("password2")

        password = validated_data.pop("password")

        student_id = validated_data.pop("student_id", "")
        department = validated_data.pop("department", "")
        program = validated_data.pop("program", "")
        year_of_study = validated_data.pop("year_of_study", None)

        user = CustomUser.objects.create_user(
            username=validated_data.get("username"),
            email=validated_data.get("email"),
            password=password,
            role="student"
        )

        StudentProfile.objects.create(
            user=user,
            student_id=student_id,
            department=department,
            program=program,
            year_of_study=year_of_study
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    student_profile = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "role",
            "student_profile",
        ]

    def get_student_profile(self, obj):
        if hasattr(obj, "student_profile"):
            return {
                "student_id": obj.student_profile.student_id,
                "department": obj.student_profile.department,
                "program": obj.student_profile.program,
                "year_of_study": obj.student_profile.year_of_study,
            }
        return None


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = "__all__"