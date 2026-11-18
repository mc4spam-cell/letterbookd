from datetime import date, timedelta

import pytest
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


def _add_member(club, user):
    Membership.objects.create(user=user, club=club, role=Role.MEMBER)


@pytest.mark.django_db
def test_full_cycle_propose_vote_close(make_user, make_club, two_books):
    a, b = two_books
    host = make_user()
    m1 = make_user()
    m2 = make_user()
    club = make_club(host)
    _add_member(club, m1)
    _add_member(club, m2)

    # Propositions
    _login(m1).post(reverse("propose", args=[club.pk]), {"book_id": a.pk})
    _login(m2).post(reverse("propose", args=[club.pk]), {"book_id": b.pk})
    assert club.propositions.count() == 2

    # Ouverture (animateur uniquement)
    _login(m1).post(reverse("open_vote", args=[club.pk]))  # ignoré : membre
    assert not Vote.objects.filter(club=club).exists()
    _login(host).post(reverse("open_vote", args=[club.pk]))
    vote = Vote.objects.get(club=club)
    assert vote.is_open

    # Impossible d'ouvrir un second vote
    _login(host).post(reverse("open_vote", args=[club.pk]))
    assert Vote.objects.filter(club=club).count() == 1

    # Pendant un vote, on ne peut plus proposer
    r = _login(m1).post(reverse("propose", args=[club.pk]), {"book_id": a.pk})
    assert club.propositions.count() == 2
    assert b"vote est en cours" in r.content

    # Bulletins : m1 et host votent A, m2 vote B → A gagne
    prop_a = Proposition.objects.get(book=a)
    prop_b = Proposition.objects.get(book=b)
    _login(host).post(reverse("vote_detail", args=[club.pk]), {"proposition_id": prop_a.pk})
    _login(m1).post(reverse("vote_detail", args=[club.pk]), {"proposition_id": prop_a.pk})
    _login(m2).post(reverse("vote_detail", args=[club.pk]), {"proposition_id": prop_b.pk})
    assert Ballot.objects.filter(vote=vote).count() == 3

    # Double-vote interdit
    _login(m1).post(reverse("vote_detail", args=[club.pk]), {"proposition_id": prop_b.pk})
    assert Ballot.objects.filter(vote=vote, user=m1).count() == 1

    # Clôture : animateur fixe les dates
    today = date.today()
    _login(host).post(
        reverse("close_vote", args=[club.pk]),
        {"start_date": today.isoformat(), "end_date": (today + timedelta(days=30)).isoformat()},
    )
    vote.refresh_from_db()
    assert vote.closed_at is not None
    assert vote.winner_id == prop_a.pk
    # Propositions perdantes consommées
    assert not Proposition.objects.filter(pk=prop_b.pk).exists()
    # Livre du mois visible
    cur = current_selection(club)
    assert cur is not None and cur.winner.book_id == a.pk


@pytest.mark.django_db
def test_non_member_cannot_propose_or_vote(make_user, make_club, two_books):
    a, _ = two_books
    host = make_user()
    outsider = make_user()
    club = make_club(host)
    r = _login(outsider).post(reverse("propose", args=[club.pk]), {"book_id": a.pk})
    assert r.status_code == 404


@pytest.mark.django_db
def test_close_without_ballots_is_noop(make_user, make_club, two_books):
    a, _ = two_books
    host = make_user()
    club = make_club(host)
    Proposition.objects.create(club=club, book=a, proposed_by=host)
    _login(host).post(reverse("open_vote", args=[club.pk]))
    today = date.today().isoformat()
    _login(host).post(
        reverse("close_vote", args=[club.pk]),
        {"start_date": today, "end_date": today},
    )
    vote = Vote.objects.get(club=club)
    assert vote.closed_at is None
