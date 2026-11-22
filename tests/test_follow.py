import pytest
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from books.models import Book
from clubs.models import Follow, Reading


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def book(db):
    return Book.objects.create(olid="OL1W", title="A", authors="x")


@pytest.mark.django_db
def test_follow_and_unfollow(make_user):
    me = make_user()
    other = make_user()
    _login(me).post(reverse("follow", args=[other.pk]))
    assert Follow.objects.filter(follower=me, followed=other).exists()
    _login(me).post(reverse("unfollow", args=[other.pk]))
    assert not Follow.objects.filter(follower=me, followed=other).exists()


@pytest.mark.django_db
def test_cannot_self_follow(make_user):
    u = make_user()
    _login(u).post(reverse("follow", args=[u.pk]))
    assert not Follow.objects.filter(follower=u, followed=u).exists()


@pytest.mark.django_db
def test_follow_db_constraint_rejects_self(make_user):
    u = make_user()
    with pytest.raises(IntegrityError):
        Follow.objects.create(follower=u, followed=u)


@pytest.mark.django_db
def test_home_shows_only_followed_users_readings(make_user, follow, book):
    me = make_user()
    friend = make_user(email="friend@x.y", display_name="friend")
    stranger = make_user(email="stranger@x.y", display_name="stranger")
    follow(me, friend)

    book2 = Book.objects.create(olid="OL2W", title="Autre", authors="z")
    Reading.objects.create(user=friend, book=book, status="read")
    Reading.objects.create(user=stranger, book=book2, status="read")

    r = _login(me).get(reverse("home"))
    # Home affiche désormais les suivis EN HAUT, puis une tranche d'autres membres.
    # On vérifie seulement que les suivis apparaissent, pas l'absence des autres.
    assert friend.display_name.encode() in r.content
    assert book.title.encode() in r.content


@pytest.mark.django_db
def test_home_empty_state_when_following_nobody(make_user, book):
    me = make_user()
    Reading.objects.create(user=make_user(), book=book, status="read")
    r = _login(me).get(reverse("home"))
    assert b"Personne \xc3\xa0 suivre" in r.content


@pytest.mark.django_db
def test_members_page_lists_only_followed(make_user):
    """La page /membres/ ne liste que les membres que je suis."""
    me = make_user()
    followed = make_user(email="a@x.y", display_name="followed")
    other = make_user(email="other@x.y", display_name="other")
    from clubs.models import Follow
    Follow.objects.create(follower=me, followed=followed)
    r = _login(me).get(reverse("members"))
    body = r.content.decode().split('id="main"', 1)[1]
    assert followed.display_name in body
    assert other.display_name not in body
    assert me.display_name not in body
