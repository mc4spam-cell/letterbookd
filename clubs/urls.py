from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("clubs/new/", views.club_create, name="club_create"),
    path("clubs/<int:club_id>/", views.club_detail, name="club_detail"),
    path("clubs/<int:club_id>/reglages/", views.club_settings, name="club_settings"),
    path("rejoindre/<str:token>/", views.join_by_token, name="join_by_token"),
    path("membres/<int:user_id>/", views.profile_detail, name="profile_detail"),
    path("moi/", views.me_settings, name="me_settings"),
]
