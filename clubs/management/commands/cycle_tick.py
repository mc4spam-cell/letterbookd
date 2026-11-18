"""Avance le cycle du club : vote le 1er, clôture le dernier jour du mois.

À lancer une fois par jour par cron. Idempotent : relancer le même jour
ne crée ni ne clôt un vote déjà traité.
"""

from calendar import monthrange
from datetime import date

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from clubs.models import Ballot, Club, Proposition, Vote


def _end_of(d: date) -> int:
    return monthrange(d.year, d.month)[1]


def _next_month_bounds(d: date) -> tuple[date, date]:
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(y, m, 1), date(y, m, monthrange(y, m)[1])


def _close(vote: Vote, today: date) -> None:
    winner = (
        Ballot.objects.filter(vote=vote)
        .values("proposition_id")
        .annotate(n=Count("id"))
        .order_by("-n", "proposition_id")
        .first()
    )
    start, end = _next_month_bounds(today)
    vote.start_date = start
    vote.end_date = end
    if winner is not None:
        vote.winner_id = winner["proposition_id"]
        Proposition.objects.filter(club=vote.club).exclude(pk=vote.winner_id).delete()
    vote.closed_at = timezone.now()
    vote.save()


class Command(BaseCommand):
    help = "Ouvre/clôt les votes mensuels des clubs."

    def add_arguments(self, parser):
        parser.add_argument("--today", help="ISO date (YYYY-MM-DD) pour injection en test")

    def handle(self, *args, **opts):
        today = (
            date.fromisoformat(opts["today"]) if opts.get("today") else timezone.localdate()
        )
        is_first = today.day == 1
        is_last = today.day == _end_of(today)
        opened = closed = 0
        for club in Club.objects.all():
            open_vote = Vote.objects.filter(club=club, closed_at__isnull=True).first()
            if is_first and open_vote is None and club.propositions.exists():
                Vote.objects.create(club=club)
                opened += 1
            elif is_last and open_vote is not None:
                _close(open_vote, today)
                closed += 1
        self.stdout.write(f"cycle_tick {today}: ouverts={opened} clos={closed}")
