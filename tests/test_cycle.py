from datetime import date

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from books.models import Book
from clubs.cycle_views import current_selection
from clubs.models import Ballot, Membership, Proposition, Role, Vote


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

    call_command("cycle_tick", "--today=2026-11-01")
    vote = Vote.objects.get(club=club)
    assert vote.is_open
    assert vote.cycle_month == date(2026, 11, 1)
    # Idempotent le même jour
    call_command("cycle_tick", "--today=2026-11-15")
    assert Vote.objects.filter(club=club).count() == 1

    prop_a = Proposition.objects.get(book=a)
    prop_b = Proposition.objects.get(book=b)
    _login(host).post(reverse("vote_detail", args=[club.pk]), {"proposition_id": prop_a.pk})
    _login(m1).post(reverse("vote_detail", args=[club.pk]), {"proposition_id": prop_a.pk})
    _login(m2).post(reverse("vote_detail", args=[club.pk]), {"proposition_id": prop_b.pk})
    assert Ballot.objects.filter(vote=vote).count() == 3

    # Bascule de mois → clôture + nouveau vote si propositions restent
    call_command("cycle_tick", "--today=2026-12-01")
    vote.refresh_from_db()
    assert vote.closed_at is not None
    assert vote.winner_id == prop_a.pk
    assert vote.start_date == date(2026, 12, 1)
    assert vote.end_date == date(2026, 12, 31)
    assert not Proposition.objects.filter(pk=prop_b.pk).exists()
    cur = current_selection(club)
    assert cur is not None and cur.winner.book_id == a.pk


@pytest.mark.django_db
def test_no_vote_opens_without_propositions(make_user, make_club):
    club = make_club(make_user())
    call_command("cycle_tick", "--today=2026-11-01")
    assert not Vote.objects.filter(club=club).exists()


@pytest.mark.django_db
def test_close_without_ballots_sets_dates_but_no_winner(make_user, make_club, two_books):
    a, _ = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    call_command("cycle_tick", "--today=2026-11-01")
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
    _login(host).post(
        reverse("vote_detail", args=[club.pk]),
        {"proposition_id": Proposition.objects.get(book=a).pk},
    )
    call_command("cycle_tick", "--today=2027-01-01")
    v = Vote.objects.get(club=club, cycle_month=date(2026, 12, 1))
    assert v.start_date == date(2027, 1, 1)
    assert v.end_date == date(2027, 1, 31)


@pytest.mark.django_db
def test_catch_up_opens_mid_month(make_user, make_club, two_books):
    """Si cycle_tick n'a pas tourné le 1er, il rattrape plus tard."""
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
    """Si cycle_tick n'a pas tourné au changement de mois, il rattrape."""
    a, _ = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    call_command("cycle_tick", "--today=2026-11-01")
    _login(host).post(
        reverse("vote_detail", args=[club.pk]),
        {"proposition_id": Proposition.objects.get(book=a).pk},
    )
    # Serveur éteint au 30 novembre et au 1er décembre ; ne redémarre que le 15.
    call_command("cycle_tick", "--today=2026-12-15")
    v = Vote.objects.get(club=club, cycle_month=date(2026, 11, 1))
    assert v.closed_at is not None
    assert v.start_date == date(2026, 12, 1)
    assert v.end_date == date(2026, 12, 31)


@pytest.mark.django_db
def test_cycle_already_ran_this_month_is_not_reopened(make_user, make_club, two_books):
    a, _ = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    call_command("cycle_tick", "--today=2026-11-01")
    # Scénario : le vote est clos avant la fin du mois (edge, ex. maintenance).
    v = Vote.objects.get(club=club)
    from django.utils import timezone
    v.closed_at = timezone.now()
    v.save()
    # cycle_tick repasse dans le même mois → ne rouvre rien.
    call_command("cycle_tick", "--today=2026-11-20")
    assert Vote.objects.filter(club=club, cycle_month=date(2026, 11, 1)).count() == 1


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
