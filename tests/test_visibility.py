"""Tests d'isolation : porte 1 du projet.

Ces tests décrivent la règle centrale (une seule) : A voit B ssi A et B
partagent un club. Ils sont écrits avant toute vue qui lit des données.
"""

import pytest
from django.contrib.auth.models import AnonymousUser

from clubs.models import Membership, Role
from clubs.visibility import shares_club_with, visible_clubs, visible_users


@pytest.mark.django_db
def test_user_sees_self(make_user):
    u = make_user()
    assert shares_club_with(u, u) is True


def test_anonymous_sees_nothing(make_user):
    u = make_user()
    anon = AnonymousUser()
    assert shares_club_with(anon, u) is False
    assert visible_users(anon).count() == 0
    assert visible_clubs(anon).count() == 0


def test_members_of_same_club_see_each_other(make_user, make_club):
    a = make_user()
    b = make_user()
    club = make_club(a)
    Membership.objects.create(user=b, club=club, role=Role.MEMBER)
    assert shares_club_with(a, b) is True
    assert shares_club_with(b, a) is True
    assert b in visible_users(a)
    assert a in visible_users(b)


def test_members_of_different_clubs_are_invisible(make_user, make_club):
    a = make_user()
    b = make_user()
    make_club(a, name="c1")
    make_club(b, name="c2")
    assert shares_club_with(a, b) is False
    assert b not in visible_users(a)
    assert a not in visible_users(b)


def test_excluded_member_loses_visibility(make_user, make_club):
    a = make_user()
    b = make_user()
    club = make_club(a)
    m = Membership.objects.create(user=b, club=club, role=Role.MEMBER)
    assert shares_club_with(a, b) is True
    m.delete()
    assert shares_club_with(a, b) is False
    assert b not in visible_users(a)


def test_visible_clubs_only_lists_my_clubs(make_user, make_club):
    a = make_user()
    b = make_user()
    mine = make_club(a, name="à moi")
    make_club(b, name="à lui")
    clubs_a = list(visible_clubs(a))
    assert clubs_a == [mine]
