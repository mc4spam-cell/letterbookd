import pytest
from django.test import Client
from django.urls import reverse

from books.models import Book
from clubs.models import Suggestion


@pytest.fixture
def book(db):
    return Book.objects.create(olid="OLSUG1W", title="Suggéré", authors="X")


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_suggest_requires_following(make_user, book):
    me = make_user()
    other = make_user()
    _login(me).post(
        reverse("book_suggest", args=[book.pk]),
        {"recipient_id": other.pk, "message": "tiens"},
        secure=True,
    )
    assert not Suggestion.objects.filter(sender=me, recipient=other).exists()


@pytest.mark.django_db
def test_suggest_creates_and_appears_in_notifications(make_user, follow, book):
    me = make_user()
    other = make_user()
    follow(me, other)
    _login(me).post(
        reverse("book_suggest", args=[book.pk]),
        {"recipient_id": other.pk, "message": "regarde"},
        secure=True,
    )
    s = Suggestion.objects.get(sender=me, recipient=other, book=book)
    assert s.message == "regarde"
    assert s.read_at is None

    page = _login(other).get(reverse("notifications"), secure=True)
    assert page.status_code == 200
    assert "te suggère".encode() in page.content

    _login(other).post(reverse("notifications"), secure=True)
    s.refresh_from_db()
    assert s.read_at is not None
