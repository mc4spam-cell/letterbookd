import io
import json
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from books import openlibrary
from books.models import Book

SAMPLE = {
    "docs": [
        {
            "key": "/works/OL27448W",
            "title": "L'Étranger",
            "author_name": ["Albert Camus"],
            "isbn": ["9782070360024"],
            "number_of_pages_median": 159,
            "cover_i": 12345,
            "first_publish_year": 1942,
        }
    ]
}


def _fake_urlopen(*_a, **_k):
    return io.BytesIO(json.dumps(SAMPLE).encode("utf-8"))


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_search_returns_normalised_results(make_user):
    with patch.object(openlibrary, "urlopen", _fake_urlopen):
        r = _login(make_user()).get(reverse("books_search"), {"q": "camus"})
    assert r.status_code == 200
    assert b"Albert Camus" in r.content


@pytest.mark.django_db
def test_add_creates_local_copy_without_network(make_user):
    c = _login(make_user())
    r = c.post(
        reverse("books_add"),
        {
            "olid": "OL27448W",
            "title": "L'Étranger",
            "authors": "Albert Camus",
            "isbn": "9782070360024",
            "pages": "159",
            "year": "1942",
            "cover_id": "12345",
        },
    )
    book = Book.objects.get(olid="OL27448W")
    assert r.status_code == 302
    assert book.title == "L'Étranger"
    assert book.pages == 159


@pytest.mark.django_db
def test_add_is_idempotent(make_user):
    c = _login(make_user())
    data = {"olid": "OL1W", "title": "T", "authors": "A"}
    c.post(reverse("books_add"), data)
    c.post(reverse("books_add"), data)
    assert Book.objects.filter(olid="OL1W").count() == 1


@pytest.mark.django_db
def test_add_with_next_rate_redirects_to_rating(make_user):
    c = _login(make_user())
    r = c.post(
        reverse("books_add"),
        {"olid": "OLX", "title": "T", "authors": "A", "next": "rate"},
    )
    assert r.status_code == 302
    book = Book.objects.get(olid="OLX")
    assert r["Location"] == reverse("read_book", args=[book.pk])


@pytest.mark.django_db
def test_add_with_next_list_redirects_to_list_picker(make_user):
    c = _login(make_user())
    r = c.post(
        reverse("books_add"),
        {"olid": "OLY", "title": "T", "authors": "A", "next": "list"},
    )
    book = Book.objects.get(olid="OLY")
    assert r["Location"] == reverse("book_add_to_list", args=[book.pk])


@pytest.mark.django_db
def test_inline_rate_creates_book_reading_and_returns_json(make_user):
    import json

    u = make_user()
    r = _login(u).post(
        reverse("books_add"),
        {
            "olid": "OLZ",
            "title": "T",
            "authors": "A",
            "next": "inline_rate",
            "rating": "7",
        },
    )
    assert r.status_code == 200
    data = json.loads(r.content)
    assert data["rating"] == 7
    book = Book.objects.get(olid="OLZ")
    assert data["book_id"] == book.pk
    from clubs.models import Reading
    assert Reading.objects.get(user=u, book=book).rating == 7


@pytest.mark.django_db
def test_inline_rate_updates_existing_reading(make_user):
    u = make_user()
    book = Book.objects.create(olid="OLY2", title="T", authors="A")
    from clubs.models import Reading
    Reading.objects.create(user=u, book=book, status="read", rating=3)
    _login(u).post(
        reverse("books_add"),
        {"olid": "OLY2", "title": "T", "next": "inline_rate", "rating": "9"},
    )
    assert Reading.objects.get(user=u, book=book).rating == 9


@pytest.mark.django_db
def test_detail_renders_offline(make_user):
    book = Book.objects.create(olid="OL2W", title="Belle du Seigneur", authors="Cohen")
    r = _login(make_user()).get(reverse("books_detail", args=[book.pk]))
    assert r.status_code == 200
    assert b"Belle du Seigneur" in r.content


def test_search_requires_login():
    r = Client().get(reverse("books_search"))
    assert r.status_code in (301, 302)


def test_openlibrary_search_empty_query_skips_network():
    with patch.object(openlibrary, "urlopen", side_effect=AssertionError("called")):
        assert openlibrary.search("") == []
        assert openlibrary.search("   ") == []
