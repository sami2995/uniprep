from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentProfile


class CustomUserAdmin(UserAdmin):
    list_display = [
        "username", "email", "role", "department", "is_active", "is_staff",
        "date_joined",
    ]
    list_filter = ["role", "is_active", "is_staff", "department"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-date_joined"]

    fieldsets = UserAdmin.fieldsets + (
        ("Institutional Role", {"fields": ("role", "department")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Institutional Role", {"fields": ("role", "department")}),
    )


class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "student_id", "department", "program", "year_of_study"]
    list_filter = ["department", "program", "year_of_study"]
    search_fields = ["user__username", "student_id"]


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
