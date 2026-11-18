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
    friend = make_user(email="friend@x.y")
    stranger = make_user(email="stranger@x.y")
    follow(me, friend)

    book2 = Book.objects.create(olid="OL2W", title="Autre", authors="z")
    Reading.objects.create(user=friend, book=book, status="read")
    Reading.objects.create(user=stranger, book=book2, status="read")

    r = _login(me).get(reverse("home"))
    assert b"Belle" not in r.content  # ignore (pas défini)
    assert friend.email.encode() in r.content
    assert stranger.email.encode() not in r.content
    assert book.title.encode() in r.content
    assert book2.title.encode() not in r.content


@pytest.mark.django_db
def test_home_empty_state_when_following_nobody(make_user, book):
    me = make_user()
    Reading.objects.create(user=make_user(), book=book, status="read")
    r = _login(me).get(reverse("home"))
    assert b"Personne \xc3\xa0 suivre" in r.content


@pytest.mark.django_db
def test_members_page_lists_others(make_user):
    me = make_user()
    make_user(email="other@x.y")
    r = _login(me).get(reverse("members"))
    content = r.content.decode()
    # Isole la liste des membres (après <main>)
    body = content.split('id="main"', 1)[1]
    assert "other@x.y" in body
    assert me.email not in body
