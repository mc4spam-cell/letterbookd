from django.urls import path

from . import list_views, moderation_views, review_views, views

urlpatterns = [
    path("", views.home, name="home"),
    path("membres/", views.members, name="members"),
    path("membres/<int:user_id>/", views.profile_detail, name="profile_detail"),
    path("membres/<int:user_id>/suivre/", views.follow, name="follow"),
    path("membres/<int:user_id>/ne-plus-suivre/", views.unfollow, name="unfollow"),
    path(
        "membres/<int:user_id>/lectures/",
        review_views.profile_readings,
        name="profile_readings",
    ),
    path("livres/<int:book_id>/lire/", review_views.read_book, name="read_book"),
    path("avis/<int:review_id>/", review_views.review_detail, name="review_detail"),
    path("avis/<int:review_id>/reagir/", review_views.react_to_review, name="react_to_review"),
    path("flux/", review_views.feed, name="feed"),
    path("notifications/", review_views.notifications, name="notifications"),
    path("stats/", review_views.stats, name="stats"),
    path("listes/", list_views.lists_index, name="lists_index"),
    path("listes/nouvelle/", list_views.list_create, name="list_create"),
    path(
        "listes/<int:list_id>/retirer/<int:item_id>/",
        list_views.list_remove,
        name="list_remove",
    ),
    path("listes/<int:list_id>/supprimer/", list_views.list_delete, name="list_delete"),
    path("mes-lectures/<int:reading_id>/supprimer/", list_views.reading_delete, name="reading_delete"),
    path(
        "livres/<int:book_id>/ajouter-liste/",
        list_views.book_add_to_list,
        name="book_add_to_list",
    ),
    path("moi/", views.me_settings, name="me_settings"),
    path("inviter/", views.invites, name="invites"),
    path("invitation/<str:token>/", views.accept_invitation, name="accept_invitation"),
    path("moderation/", moderation_views.moderation, name="moderation"),
    path(
        "moderation/membre/<int:user_id>/<str:action>/",
        moderation_views.moderation_user_action,
        name="moderation_user_action",
    ),
    path(
        "moderation/<str:kind>/<int:obj_id>/supprimer/",
        moderation_views.moderation_delete,
        name="moderation_delete",
    ),
]
