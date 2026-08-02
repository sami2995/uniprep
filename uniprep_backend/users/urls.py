from django.urls import path
from .views import RegisterView, change_password, current_user, admin_create_user


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", current_user, name="current-user"),
    path("change-password/", change_password, name="change-password"),
    path("admin-create-user/", admin_create_user, name="admin-create-user"),
]