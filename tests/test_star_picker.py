import pytest
from django.test import Client
from django.urls import reverse

from books.models import Book


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_picker_renders_ten_half_stars(make_user):
    book = Book.objects.create(olid="OL1W", title="T", authors="A")
    r = _login(make_user()).get(reverse("read_book", args=[book.pk]))
    content = r.content.decode()
    assert content.count('class="star-half') == 10
    # Chaque valeur de 1..10 est exposée
    for v in range(1, 11):
        assert f'value="{v}"' in content
    # Option « pas de note »
    assert "pas de note" in content


@pytest.mark.django_db
def test_picker_reflects_current_rating(make_user):
    book = Book.objects.create(olid="OL2W", title="T", authors="A")
    u = make_user()
    _login(u).post(reverse("read_book", args=[book.pk]), {"rating": "7"})
    r = _login(u).get(reverse("read_book", args=[book.pk]))
    content = r.content.decode()
    # Le radio de valeur 7 est coché
    assert 'value="7" checked' in content or 'value="7"\n           checked' in content


@pytest.mark.django_db
def test_posting_rating_from_picker_persists(make_user):
    book = Book.objects.create(olid="OL3W", title="T", authors="A")
    u = make_user()
    _login(u).post(reverse("read_book", args=[book.pk]), {"rating": "5"})
    from clubs.models import Reading
    assert Reading.objects.get(user=u, book=book).rating == 5
