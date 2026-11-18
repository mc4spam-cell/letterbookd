"""Règle centrale de visibilité.

Un utilisateur A peut voir les données d'un utilisateur B si et seulement si
A et B partagent au moins un club. Tout accès aux données d'un membre passe
par `shares_club_with` ou par les querysets dérivés.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, QuerySet

from .models import Membership


def shares_club_with(viewer, other) -> bool:
    if not getattr(viewer, "is_authenticated", False):
        return False
    if not getattr(other, "is_authenticated", True):
        return False
    if viewer.pk == getattr(other, "pk", None):
        return True
    viewer_clubs = Membership.objects.filter(user=viewer).values("club_id")
    return Membership.objects.filter(user=other, club_id__in=viewer_clubs).exists()


def visible_users(viewer) -> QuerySet:
    """Les utilisateurs que le viewer est autorisé à voir (lui inclus)."""
    User = get_user_model()
    if not getattr(viewer, "is_authenticated", False):
        return User.objects.none()
    viewer_clubs = Membership.objects.filter(user=viewer).values("club_id")
    shared = Membership.objects.filter(user=OuterRef("pk"), club_id__in=viewer_clubs)
    return User.objects.filter(pk=viewer.pk) | User.objects.annotate(
        _shared=Exists(shared)
    ).filter(_shared=True)


def visible_clubs(viewer) -> QuerySet:
    from .models import Club

    if not getattr(viewer, "is_authenticated", False):
        return Club.objects.none()
    return Club.objects.filter(membership__user=viewer).distinct()


def visible_reviews(viewer) -> QuerySet:
    from .models import Review

    if not getattr(viewer, "is_authenticated", False):
        return Review.objects.none()
    return Review.objects.filter(reading__user__in=visible_users(viewer)).distinct()


def visible_lists(viewer) -> QuerySet:
    from .models import ReadingList

    if not getattr(viewer, "is_authenticated", False):
        return ReadingList.objects.none()
    return ReadingList.objects.filter(owner__in=visible_users(viewer)).distinct()
