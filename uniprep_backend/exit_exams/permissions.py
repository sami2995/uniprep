from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and (user.is_staff or getattr(user, "role", None) == "admin")
        )


class IsStudentRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "student"
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

        return request.user.is_staff or getattr(request.user, "role", None) == "admin"