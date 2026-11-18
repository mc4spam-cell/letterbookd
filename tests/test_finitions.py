import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from books.models import Book
from clubs.models import Membership, Role


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
    assert b"8" in r.content  # moyenne
    assert str(timezone.now().year).encode() in r.content


@pytest.mark.django_db
def test_sole_host_cannot_delete_account(make_user, make_club):
    u = make_user()
    make_club(u)
    r = _login(u).post(reverse("me_settings"), {"action": "delete"})
    assert r.status_code == 200  # ré-affiche avec erreur, pas de suppression
    from django.contrib.auth import get_user_model
    assert get_user_model().objects.filter(pk=u.pk).exists()


@pytest.mark.django_db
def test_promote_then_delete_works(make_user, make_club):
    host = make_user()
    member = make_user()
    club = make_club(host)
    Membership.objects.create(user=member, club=club, role=Role.MEMBER)
    _login(host).post(
        reverse("club_settings", args=[club.pk]),
        {"action": "promote", "user_id": member.pk},
    )
    assert Membership.objects.get(user=member, club=club).role == Role.HOST
    _login(host).post(reverse("me_settings"), {"action": "delete"})
    from django.contrib.auth import get_user_model
    assert not get_user_model().objects.filter(pk=host.pk).exists()
    # Le club garde toujours un animateur
    assert Membership.objects.filter(club=club, role=Role.HOST).exists()


@pytest.mark.django_db
def test_promote_only_by_host(make_user, make_club):
    host = make_user()
    member = make_user()
    other = make_user()
    club = make_club(host)
    Membership.objects.create(user=member, club=club, role=Role.MEMBER)
    Membership.objects.create(user=other, club=club, role=Role.MEMBER)
    r = _login(member).post(
        reverse("club_settings", args=[club.pk]),
        {"action": "promote", "user_id": other.pk},
    )
    assert r.status_code == 404
    assert Membership.objects.get(user=other, club=club).role == Role.MEMBER


@pytest.mark.django_db
def test_skip_link_present(make_user):
    r = _login(make_user()).get(reverse("home"))
    assert b'href="#main"' in r.content
    assert b'id="main"' in r.content
