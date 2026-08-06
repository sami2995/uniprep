from rest_framework.permissions import BasePermission, SAFE_METHODS


ADMIN_ROLES = {"department_head", "system_admin", "admin"}


class IsSystemAdminOnly(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "system_admin"
        )


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and (user.is_staff or getattr(user, "role", None) in ADMIN_ROLES)
        )


class IsDepartmentHeadOrSystemAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and (
                user.is_staff
                or getattr(user, "role", None)
                in {"department_head", "system_admin", "admin"}
            )
        )


class IsStudentRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "student"
        )


class IsTeacherRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "teacher"
        )


class IsDepartmentHeadRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and getattr(user, "role", None) in {"department_head", "admin"}
        )


class IsAdminOrReadOnly(BasePermission):
    """
    Admin can create/update/delete.
    Authenticated students can only read.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.user.is_staff or getattr(request.user, "role", None) in ADMIN_ROLES


class IsSystemAdminOrReadOnly(BasePermission):
    """
    Only system_admin (or Django is_staff) can create/update/delete.
    All authenticated users can read.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.user.is_staff or getattr(request.user, "role", None) == "system_admin"

