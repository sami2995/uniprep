from django.urls import path
from .views import RegisterView, current_user


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", current_user, name="current-user"),
]