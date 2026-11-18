from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from books.models import Book

from .models import Ballot, Club, Membership, Proposition, Vote


def _membership(user, club):
    return Membership.objects.filter(user=user, club=club).first()


def _require_member(user, club_id):
    club = get_object_or_404(Club, pk=club_id)
    me = _membership(user, club)
    if me is None:
        raise Http404
    return club, me


@login_required
def propose(request, club_id):
    club, me = _require_member(request.user, club_id)
    if request.method == "POST":
        book_id = request.POST.get("book_id")
        book = get_object_or_404(Book, pk=book_id)
        Proposition.objects.get_or_create(
            club=club, book=book, defaults={"proposed_by": request.user}
        )
        return redirect("club_detail", club_id=club.pk)
    return render(
        request, "clubs/propose.html", {"club": club, "books": Book.objects.all()}
    )


@login_required
def vote_detail(request, club_id):
    club, me = _require_member(request.user, club_id)
    vote = Vote.objects.filter(club=club, closed_at__isnull=True).first()
    if vote is None:
        return redirect("club_detail", club_id=club.pk)
    my_ballot = Ballot.objects.filter(vote=vote, user=request.user).first()
    if request.method == "POST" and my_ballot is None:
        prop_id = request.POST.get("proposition_id")
        prop = get_object_or_404(Proposition, pk=prop_id, club=club)
        Ballot.objects.create(vote=vote, user=request.user, proposition=prop)
        return redirect("vote_detail", club_id=club.pk)
    propositions = club.propositions.select_related("book").annotate(
        ballots_count=Count("ballot", filter=Q(ballot__vote=vote))
    )
    return render(
        request,
        "clubs/vote.html",
        {
            "club": club,
            "vote": vote,
            "propositions": propositions,
            "my_ballot": my_ballot,
        },
    )


def current_selection(club) -> Vote | None:
    today = date.today()
    return (
        Vote.objects.filter(
            club=club,
            closed_at__isnull=False,
            winner__isnull=False,
        )
        .filter(end_date__gte=today)
        .order_by("-closed_at")
        .first()
    )


def past_selections(club):
    return (
        Vote.objects.filter(club=club, closed_at__isnull=False, winner__isnull=False)
        .select_related("winner__book")
        .order_by("-closed_at")
    )
