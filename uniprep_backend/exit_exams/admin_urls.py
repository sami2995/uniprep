from django.urls import path
from .views import (
    system_settings,
    list_users,
    admin_user_detail,
    list_department_teachers,
    toggle_user_active,
    admin_reset_password,
    admin_department_detail,
    admin_audit_log_list,
    verify_user,
    pending_verification_users,
)

urlpatterns = [
    path("settings/", system_settings, name="admin-system-settings"),
    path("users/", list_users, name="admin-list-users"),
    path("users/<int:user_id>/", admin_user_detail, name="admin-user-detail"),
    path("users/<int:user_id>/toggle-active/", toggle_user_active, name="admin-toggle-user-active"),
    path("users/<int:user_id>/reset-password/", admin_reset_password, name="admin-reset-password"),
    path("users/<int:user_id>/verify/", verify_user, name="admin-verify-user"),
    path("users/pending-verification/", pending_verification_users, name="admin-pending-verification-users"),
    path("teachers/", list_department_teachers, name="admin-list-teachers"),
    path("departments/<int:pk>/", admin_department_detail, name="admin-department-detail"),
    path("audit-log/", admin_audit_log_list, name="admin-audit-log-list"),
]
