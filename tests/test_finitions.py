import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from books.models import Book


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_stats_page_sums_readings(make_user):
    u = make_user()
    book = Book.objects.create(olid="OL1W", title="A", authors="x")
    _login(u).post(reverse("read_book", args=[book.pk]), {"status": "read", "rating": "8"})
    r = _login(u).get(reverse("stats"))
    assert r.status_code == 200
    assert b"8" in r.content
    assert str(timezone.now().year).encode() in r.content


@pytest.mark.django_db
def test_skip_link_present(make_user):
    r = _login(make_user()).get(reverse("home"))
    assert b'href="#main"' in r.content
    assert b'id="main"' in r.content


@pytest.mark.django_db
def test_delete_account_cleans_up(make_user):
    u = make_user()
    _login(u).post(reverse("me_settings"), {"action": "delete"})
    from django.contrib.auth import get_user_model
    assert not get_user_model().objects.filter(pk=u.pk).exists()
