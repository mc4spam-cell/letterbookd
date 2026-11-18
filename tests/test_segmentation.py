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


def _section(content: str, club_name: str) -> str:
    """Extrait le fragment de la section d'un club donné (jusqu'à la suivante)."""
    marker = f">{club_name}<"
    i = content.find(marker)
    assert i != -1, f"section {club_name} introuvable"
    next_h2 = content.find("<h2>", i + 1)
    return content[i : next_h2 if next_h2 != -1 else len(content)]


@pytest.mark.django_db
def test_feed_shows_one_section_per_club_with_right_reviews(make_user, make_club, book):
    me = make_user()
    friend1 = make_user(email="friend1@x.y")
    friend2 = make_user(email="friend2@x.y")
    c1 = make_club(me, name="Alpha")
    c2 = make_club(me, name="Beta")
    _member(c1, friend1)
    _member(c2, friend2)

    book2 = Book.objects.create(olid="OL2W", title="B", authors="y")
    _login(friend1).post(reverse("read_book", args=[book.pk]), {"review_text": "r1"})
    _login(friend2).post(reverse("read_book", args=[book2.pk]), {"review_text": "r2"})

    r = _login(me).get(reverse("feed"))
    content = r.content.decode()
    sec_alpha = _section(content, "Alpha")
    sec_beta = _section(content, "Beta")
    assert "friend1@" in sec_alpha and "friend2@" not in sec_alpha
    assert "friend2@" in sec_beta and "friend1@" not in sec_beta


@pytest.mark.django_db
def test_notifications_sections_scope_by_club(make_user, make_club, book):
    me = make_user()
    f1 = make_user(email="f1@x.y")
    f2 = make_user(email="f2@x.y")
    c1 = make_club(me, name="Alpha")
    c2 = make_club(me, name="Beta")
    _member(c1, f1)
    _member(c2, f2)

    _login(me).post(reverse("read_book", args=[book.pk]), {"review_text": "a"})
    from clubs.models import Review
    review = Review.objects.get()
    _login(f1).post(reverse("review_detail", args=[review.pk]), {"text": "hop1"})
    _login(f2).post(reverse("review_detail", args=[review.pk]), {"text": "hop2"})

    r = _login(me).get(reverse("notifications"))
    content = r.content.decode()
    assert "f1@" in _section(content, "Alpha")
    assert "f2@" in _section(content, "Beta")
    assert "f2@" not in _section(content, "Alpha")
    assert "f1@" not in _section(content, "Beta")


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


@pytest.mark.django_db
def test_rating_picker_in_read_book_form(make_user, book):
    u = make_user()
    r = _login(u).get(reverse("read_book", args=[book.pk]))
    assert b"<select name=\"rating\"" in r.content
    assert "★★★★★".encode() in r.content
    # L'ancien input number pour la note a disparu
    assert b'<input type="number" name="rating"' not in r.content
