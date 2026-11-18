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
    return User.objects.all() if _auth(viewer) else User.objects.none()


def visible_reviews(viewer) -> QuerySet:
    return Review.objects.all() if _auth(viewer) else Review.objects.none()


def visible_lists(viewer) -> QuerySet:
    return ReadingList.objects.all() if _auth(viewer) else ReadingList.objects.none()


def followed_ids(viewer) -> list[int]:
    if not _auth(viewer):
        return []
    return list(
        Follow.objects.filter(follower=viewer).values_list("followed_id", flat=True)
    )
