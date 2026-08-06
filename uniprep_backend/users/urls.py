from django.urls import path
from .views import (
    RegisterView,
    change_password,
    current_user,
    admin_create_user,
    registration_departments,
)


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("registration-departments/", registration_departments, name="registration-departments"),
    path("me/", current_user, name="current-user"),
    path("change-password/", change_password, name="change-password"),
    path("admin-create-user/", admin_create_user, name="admin-create-user"),
]
