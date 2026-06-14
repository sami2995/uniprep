from django.urls import path

from .views import (
    create_challenge,
    join_challenge,
    challenge_detail,
    start_challenge,
    challenge_questions,
    submit_challenge,
    challenge_leaderboard,
)

urlpatterns = [
    path("challenges/create/", create_challenge, name="create-challenge"),
    path("challenges/join/", join_challenge, name="join-challenge"),
    path("challenges/<str:room_code>/", challenge_detail, name="challenge-detail"),
    path("challenges/<str:room_code>/start/", start_challenge, name="start-challenge"),
    path("challenges/<str:room_code>/questions/", challenge_questions, name="challenge-questions"),
    path("challenges/<str:room_code>/submit/", submit_challenge, name="submit-challenge"),
    path("challenges/<str:room_code>/leaderboard/", challenge_leaderboard, name="challenge-leaderboard"),
]