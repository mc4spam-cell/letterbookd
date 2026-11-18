from datetime import date

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from books.models import Book
from clubs.cycle_views import current_selection
from clubs.models import Membership, Proposition, Reading, Role, Vote


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def two_books(db):
    return (
        Book.objects.create(olid="OL1W", title="A", authors="x"),
        Book.objects.create(olid="OL2W", title="B", authors="y"),
    )


def _member(club, user):
    Membership.objects.create(user=user, club=club, role=Role.MEMBER)


def _rate(user, book, rating):
    Reading.objects.update_or_create(
        user=user, book=book, defaults={"status": "read", "rating": rating}
    )


@pytest.mark.django_db
def test_full_cycle_auto(make_user, make_club, two_books):
    a, b = two_books
    host = make_user()
    m1 = make_user()
    m2 = make_user()
    club = make_club(host)
    _member(club, m1)
    _member(club, m2)

    _login(m1).post(reverse("propose", args=[club.pk]), {"book_id": a.pk})
    _login(m2).post(reverse("propose", args=[club.pk]), {"book_id": b.pk})

    # Ouverture automatique du cycle de novembre
    call_command("cycle_tick", "--today=2026-11-01")
    vote = Vote.objects.get(club=club)
    assert vote.is_open
    # Idempotent
    call_command("cycle_tick", "--today=2026-11-15")
    assert Vote.objects.filter(club=club).count() == 1

    # Les membres notent. A : 8 et 9 (moy 8,5). B : 6 et 7 (moy 6,5). A gagne.
    _rate(host, a, 8)
    _rate(m1, a, 9)
    _rate(m2, b, 6)
    _rate(host, b, 7)

    # Bascule de mois : clôture automatique
    call_command("cycle_tick", "--today=2026-12-01")
    vote.refresh_from_db()
    assert vote.closed_at is not None
    assert vote.winner is not None and vote.winner.book_id == a.pk
    assert vote.start_date == date(2026, 12, 1)
    assert vote.end_date == date(2026, 12, 31)
    # Perdante consommée
    assert not Proposition.objects.filter(book=b, club=club).exists()
    # Livre du mois visible
    cur = current_selection(club)
    assert cur is not None and cur.winner.book_id == a.pk


@pytest.mark.django_db
def test_no_vote_opens_without_propositions(make_user, make_club):
    club = make_club(make_user())
    call_command("cycle_tick", "--today=2026-11-01")
    assert not Vote.objects.filter(club=club).exists()


@pytest.mark.django_db
def test_close_without_any_rating_sets_dates_but_no_winner(make_user, make_club, two_books):
    a, _ = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    call_command("cycle_tick", "--today=2026-11-01")
    # Personne n'a noté → pas de gagnant
    call_command("cycle_tick", "--today=2026-12-01")
    v = Vote.objects.get(club=club, cycle_month=date(2026, 11, 1))
    assert v.closed_at is not None
    assert v.winner_id is None
    assert v.start_date == date(2026, 12, 1)
    assert current_selection(club) is None


@pytest.mark.django_db
def test_december_rolls_to_january(make_user, make_club, two_books):
    a, _ = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    call_command("cycle_tick", "--today=2026-12-01")
    _rate(host, a, 7)
    call_command("cycle_tick", "--today=2027-01-01")
    v = Vote.objects.get(club=club, cycle_month=date(2026, 12, 1))
    assert v.start_date == date(2027, 1, 1)
    assert v.end_date == date(2027, 1, 31)
    assert v.winner.book_id == a.pk


@pytest.mark.django_db
def test_catch_up_opens_mid_month(make_user, make_club, two_books):
    a, _ = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    call_command("cycle_tick", "--today=2026-11-15")
    v = Vote.objects.get(club=club)
    assert v.is_open
    assert v.cycle_month == date(2026, 11, 1)


@pytest.mark.django_db
def test_catch_up_closes_after_missed_boundary(make_user, make_club, two_books):
    a, _ = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    call_command("cycle_tick", "--today=2026-11-01")
    _rate(host, a, 9)
    # Serveur éteint fin novembre + début décembre ; redémarrage le 15.
    call_command("cycle_tick", "--today=2026-12-15")
    v = Vote.objects.get(club=club, cycle_month=date(2026, 11, 1))
    assert v.closed_at is not None
    assert v.winner.book_id == a.pk


@pytest.mark.django_db
def test_cycle_already_ran_this_month_is_not_reopened(make_user, make_club, two_books):
    a, _ = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    call_command("cycle_tick", "--today=2026-11-01")
    v = Vote.objects.get(club=club)
    from django.utils import timezone
    v.closed_at = timezone.now()
    v.save()
    call_command("cycle_tick", "--today=2026-11-20")
    assert Vote.objects.filter(club=club, cycle_month=date(2026, 11, 1)).count() == 1


@pytest.mark.django_db
def test_only_members_ratings_count(make_user, make_club, two_books):
    """Un étranger au club ne pèse pas dans la moyenne."""
    a, b = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    Proposition.objects.create(club=club, book=b, proposed_by=host)
    outsider = make_user()
    make_club(outsider, name="autre")
    _rate(host, a, 5)
    _rate(host, b, 6)
    _rate(outsider, a, 10)  # ne compte pas
    call_command("cycle_tick", "--today=2026-11-01")
    call_command("cycle_tick", "--today=2026-12-01")
    v = Vote.objects.get(club=club, cycle_month=date(2026, 11, 1))
    assert v.winner.book_id == b.pk


@pytest.mark.django_db
def test_propose_still_allowed_during_vote(make_user, make_club, two_books):
    a, b = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    call_command("cycle_tick", "--today=2026-11-01")
    _login(host).post(reverse("propose", args=[club.pk]), {"book_id": b.pk})
    assert club.propositions.count() == 2


@pytest.mark.django_db
def test_non_member_cannot_propose(make_user, make_club, two_books):
    a, _ = two_books
    outsider = make_user()
    club = make_club(make_user())
    r = _login(outsider).post(reverse("propose", args=[club.pk]), {"book_id": a.pk})
    assert r.status_code == 404
