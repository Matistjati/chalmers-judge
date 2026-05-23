from django.urls import path

from omogenjudge.frontend.leaderboard.view_leaderboard import view_leaderboard

urlpatterns = [
    path('', view_leaderboard, name='leaderboard'),
]
