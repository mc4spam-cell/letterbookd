"""Visibilité : la communauté est unique.

Tout utilisateur authentifié voit les autres membres et leurs contenus.
L'abonnement (`Follow`) ne restreint pas l'accès ; il alimente l'accueil.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from .models import Follow, ReadingList, Review


def _auth(viewer) -> bool:
    return bool(getattr(viewer, "is_authenticated", False))


def visible_users(viewer) -> QuerySet:
    User = get_user_model()
    if not _auth(viewer):
        return User.objects.none()
    return User.objects.filter(is_deleted=False)


def visible_reviews(viewer) -> QuerySet:
    if not _auth(viewer):
        return Review.objects.none()
    return Review.objects.filter(reading__user__is_deleted=False)


def visible_lists(viewer) -> QuerySet:
    if not _auth(viewer):
        return ReadingList.objects.none()
    return ReadingList.objects.filter(owner__is_deleted=False)


def followed_ids(viewer) -> list[int]:
    if not _auth(viewer):
        return []
    return list(
        Follow.objects.filter(
            follower=viewer, followed__is_deleted=False
        ).values_list("followed_id", flat=True)
    )
