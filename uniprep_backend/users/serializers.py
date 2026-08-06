from rest_framework import serializers
from .models import CustomUser, StudentProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, min_length=6)

    student_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    department = serializers.CharField(write_only=True, required=True)
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

    def validate_department(self, value):
        if not value:
            return value
        from exit_exams.models import Department
        if not Department.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                "Selected department does not match any existing department."
            )
        return value

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
        department_name = validated_data.pop("department", "")
        program = validated_data.pop("program", "")
        year_of_study = validated_data.pop("year_of_study", None)

        from exit_exams.models import Department
        department = None
        if department_name:
            department = Department.objects.filter(
                name__iexact=department_name
            ).first()

        user = CustomUser.objects.create_user(
            username=validated_data.get("username"),
            email=validated_data.get("email"),
            password=password,
            role=CustomUser.Role.STUDENT,
            department=department,
        )

        StudentProfile.objects.create(
            user=user,
            student_id=student_id,
            department=department.name if department else "",
            program=program,
            year_of_study=year_of_study
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    student_profile = serializers.SerializerMethodField()
    department_name = serializers.CharField(
        source="department.name",
        read_only=True
    )

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "role",
            "department",
            "department_name",
            "student_profile",
            "verification",
            "verified_at",
            "rejection_reason",
        ]
        read_only_fields = [
            "id", "role", "department", "department_name", "verification",
            "verified_at", "rejection_reason",
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

    def to_internal_value(self, data):
        student_profile_data = data.get("student_profile")
        data = data.copy()
        data.pop("student_profile", None)
        values = super().to_internal_value(data)
        if student_profile_data is not None:
            values["student_profile"] = student_profile_data
        return values

    def update(self, instance, validated_data):
        student_profile_data = validated_data.pop("student_profile", None)
        instance = super().update(instance, validated_data)

        if student_profile_data and hasattr(instance, "student_profile"):
            student_profile = instance.student_profile
            for field, value in student_profile_data.items():
                if field in {"student_id", "department", "program", "year_of_study"}:
                    setattr(student_profile, field, value)
            student_profile.save()

        return instance


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id", "username", "email", "password", "role",
            "department", "department_name", "is_active",
            "date_joined", "first_name", "last_name", "verification",
            "verified_by", "verified_at", "rejection_reason",
        ]
        read_only_fields = [
            "id", "date_joined", "department_name", "verification",
            "verified_by", "verified_at", "rejection_reason",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Password is required for new users."})
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = "__all__"
