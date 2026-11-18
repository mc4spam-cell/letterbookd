"""Visibilité : communauté unique, tout utilisateur authentifié voit tout."""

import pytest
from django.contrib.auth.models import AnonymousUser

from clubs.visibility import visible_lists, visible_reviews, visible_users


@pytest.mark.django_db
def test_authenticated_user_sees_everyone(make_user):
    a = make_user()
    b = make_user()
    assert b in visible_users(a)


def test_anonymous_sees_nothing():
    anon = AnonymousUser()
    assert visible_users(anon).count() == 0
    assert visible_reviews(anon).count() == 0
    assert visible_lists(anon).count() == 0
