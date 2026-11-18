from django.urls import path

from . import cycle_views, review_views, views

urlpatterns = [
    path("", views.home, name="home"),
    path("clubs/new/", views.club_create, name="club_create"),
    path("clubs/<int:club_id>/", views.club_detail, name="club_detail"),
    path("clubs/<int:club_id>/reglages/", views.club_settings, name="club_settings"),
    path("clubs/<int:club_id>/proposer/", cycle_views.propose, name="propose"),
    path("clubs/<int:club_id>/vote/", cycle_views.vote_detail, name="vote_detail"),
    path("rejoindre/<str:token>/", views.join_by_token, name="join_by_token"),
    path("membres/<int:user_id>/", views.profile_detail, name="profile_detail"),
    path("membres/<int:user_id>/lectures/", review_views.profile_readings, name="profile_readings"),
    path("livres/<int:book_id>/lire/", review_views.read_book, name="read_book"),
    path("avis/<int:review_id>/", review_views.review_detail, name="review_detail"),
    path("flux/", review_views.feed, name="feed"),
    path("notifications/", review_views.notifications, name="notifications"),
    path("moi/", views.me_settings, name="me_settings"),
]
