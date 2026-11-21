import pytest
from django.test import Client
from django.urls import reverse

from books.models import Book
from clubs.models import ListItem, Reading, ReadingList
from clubs.visibility import visible_lists


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def book(db):
    return Book.objects.create(olid="OL1W", title="Belle du Seigneur", authors="Cohen")


@pytest.fixture
def book2(db):
    return Book.objects.create(olid="OL2W", title="L'Étranger", authors="Camus")


# — Journal & relectures ———————————————————————————————————————————————


@pytest.mark.django_db
def test_reading_stores_dates(make_user, book):
    u = make_user()
    _login(u).post(
        reverse("read_book", args=[book.pk]),
        {"status": "read", "started_on": "2026-10-01", "finished_on": "2026-10-20"},
    )
    r = Reading.objects.get(user=u, book=book)
    assert str(r.started_on) == "2026-10-01"
    assert str(r.finished_on) == "2026-10-20"


@pytest.mark.django_db
def test_nouvelle_creates_a_second_reading(make_user, book):
    u = make_user()
    c = _login(u)
    c.post(reverse("read_book", args=[book.pk]), {"status": "read", "rating": "7"})
    c.post(
        reverse("read_book", args=[book.pk]) + "?nouvelle=1",
        {"status": "read", "rating": "9", "nouvelle": "1"},
    )
    readings = Reading.objects.filter(user=u, book=book).order_by("created_at")
    assert readings.count() == 2
    assert readings[0].rating == 7 and readings[1].rating == 9


@pytest.mark.django_db
def test_invalid_date_is_ignored_not_crash(make_user, book):
    u = make_user()
    _login(u).post(
        reverse("read_book", args=[book.pk]),
        {"status": "read", "started_on": "pas une date"},
    )
    r = Reading.objects.get(user=u, book=book)
    assert r.started_on is None


# — Filtre statut ———————————————————————————————————————————————————————


@pytest.mark.django_db
def test_readings_page_filters_by_status(make_user, book, book2):
    u = make_user()
    c = _login(u)
    c.post(reverse("read_book", args=[book.pk]), {"status": "read"})
    c.post(reverse("read_book", args=[book2.pk]), {"status": "to_read"})
    r = c.get(reverse("profile_readings", args=[u.pk]) + "?status=read")
    assert b"Belle du Seigneur" in r.content
    assert b"Camus" not in r.content


# — Listes ——————————————————————————————————————————————————————————————


@pytest.mark.django_db
def test_create_list(make_user):
    u = make_user()
    r = _login(u).post(reverse("list_create"), {"name": "Mes incontournables"})
    assert r.status_code == 302
    assert ReadingList.objects.filter(name="Mes incontournables", owner=u).exists()


@pytest.mark.django_db
def test_book_add_to_list_is_idempotent(make_user, book):
    u = make_user()
    rl = ReadingList.objects.create(owner=u, name="L")
    c = _login(u)
    c.post(reverse("book_add_to_list", args=[book.pk]), {"list_id": rl.pk})
    c.post(reverse("book_add_to_list", args=[book.pk]), {"list_id": rl.pk})
    assert ListItem.objects.filter(list=rl, book=book).count() == 1


@pytest.mark.django_db
def test_remove_is_owner_only(make_user, book):
    owner = make_user()
    other = make_user()
    rl = ReadingList.objects.create(owner=owner, name="L")
    item = ListItem.objects.create(list=rl, book=book)
    r = _login(other).post(reverse("list_remove", args=[rl.pk, item.pk]))
    assert r.status_code == 404
    assert ListItem.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_list_visible_to_any_member(make_user):
    # list_detail a été supprimée ; visibilité vérifiée via la règle centrale.
    owner = make_user()
    other = make_user()
    rl = ReadingList.objects.create(owner=owner, name="Vue")
    assert rl in visible_lists(other)


@pytest.mark.django_db
def test_book_add_to_existing_list(make_user, book):
    u = make_user()
    rl = ReadingList.objects.create(owner=u, name="L")
    _login(u).post(reverse("book_add_to_list", args=[book.pk]), {"list_id": rl.pk})
    assert ListItem.objects.filter(list=rl, book=book).exists()


@pytest.mark.django_db
def test_book_add_creates_new_list(make_user, book):
    u = make_user()
    _login(u).post(
        reverse("book_add_to_list", args=[book.pk]),
        {"new_list_name": "Lus en 2026"},
    )
    rl = ReadingList.objects.get(owner=u, name="Lus en 2026")
    assert ListItem.objects.filter(list=rl, book=book).exists()


@pytest.mark.django_db
def test_book_add_rejects_other_users_list(make_user, book):
    me = make_user()
    other = make_user()
    rl = ReadingList.objects.create(owner=other, name="Pas pour toi")
    r = _login(me).post(reverse("book_add_to_list", args=[book.pk]), {"list_id": rl.pk})
    assert r.status_code == 404
    assert not ListItem.objects.filter(list=rl, book=book).exists()


@pytest.mark.django_db
def test_owner_can_delete_list(make_user):
    u = make_user()
    rl = ReadingList.objects.create(owner=u, name="L")
    _login(u).post(reverse("list_delete", args=[rl.pk]))
    assert not ReadingList.objects.filter(pk=rl.pk).exists()
