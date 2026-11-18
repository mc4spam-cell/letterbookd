import pytest
from django.test import Client
from django.urls import reverse

from books.models import Book
from clubs.models import Membership, Role


def _login(user):
    c = Client()
    c.force_login(user)
    return c


def _member(club, user):
    Membership.objects.create(user=user, club=club, role=Role.MEMBER)


@pytest.fixture
def book(db):
    return Book.objects.create(olid="OL1W", title="A", authors="x")


@pytest.mark.django_db
def test_feed_filters_by_club(make_user, make_club, book):
    """Je suis dans deux clubs ; le filtre `?club=` restreint au bon."""
    me = make_user()
    friend1 = make_user(email="friend1@x.y")
    friend2 = make_user(email="friend2@x.y")
    c1 = make_club(me, name="C1")
    c2 = make_club(me, name="C2")
    _member(c1, friend1)
    _member(c2, friend2)

    book2 = Book.objects.create(olid="OL2W", title="B", authors="y")
    _login(friend1).post(reverse("read_book", args=[book.pk]), {"review_text": "sur C1"})
    _login(friend2).post(reverse("read_book", args=[book2.pk]), {"review_text": "sur C2"})

    r = _login(me).get(reverse("feed") + f"?club={c1.pk}")
    assert b"friend1" in r.content
    assert b"friend2" not in r.content

    r = _login(me).get(reverse("feed") + f"?club={c2.pk}")
    assert b"friend2" in r.content
    assert b"friend1" not in r.content

    r = _login(me).get(reverse("feed"))  # tous
    assert b"friend1" in r.content and b"friend2" in r.content


@pytest.mark.django_db
def test_notifications_filter_by_club(make_user, make_club, book):
    me = make_user()
    friend1 = make_user(email="f1@x.y")
    friend2 = make_user(email="f2@x.y")
    c1 = make_club(me, name="C1")
    c2 = make_club(me, name="C2")
    _member(c1, friend1)
    _member(c2, friend2)

    _login(me).post(reverse("read_book", args=[book.pk]), {"review_text": "avis"})
    from clubs.models import Review
    review = Review.objects.get()
    _login(friend1).post(reverse("review_detail", args=[review.pk]), {"text": "coucou C1"})
    _login(friend2).post(reverse("review_detail", args=[review.pk]), {"text": "coucou C2"})

    r = _login(me).get(reverse("notifications") + f"?club={c1.pk}")
    assert b"f1@" in r.content
    assert b"f2@" not in r.content


@pytest.mark.django_db
def test_lists_index_shows_each_visible_member(make_user, make_club, book):
    me = make_user()
    mate = make_user(email="mate@x.y")
    stranger = make_user(email="stranger@x.y")
    c = make_club(me)
    _member(c, mate)
    make_club(stranger, name="autre")
    r = _login(me).get(reverse("lists_index"))
    assert b"Tous mes livres" in r.content
    assert b"mate@x.y" in r.content
    assert b"stranger@x.y" not in r.content


@pytest.mark.django_db
def test_readings_sort_by_author(make_user, book):
    u = make_user()
    b2 = Book.objects.create(olid="OL2W", title="Zazie", authors="Aaa Queneau")
    _login(u).post(reverse("read_book", args=[book.pk]), {"status": "read"})  # x
    _login(u).post(reverse("read_book", args=[b2.pk]), {"status": "read"})  # Aaa
    r = _login(u).get(reverse("profile_readings", args=[u.pk]) + "?tri=auteur")
    content = r.content.decode()
    assert content.index("Zazie") < content.index("A</strong>")  # Aaa avant x
