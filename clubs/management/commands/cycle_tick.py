"""Avance le cycle de chaque club.

Un vote = un mois civil, identifié par `cycle_month` (1er du mois).
À chaque passage (cron quotidien) :
- si le vote ouvert est d'un mois antérieur → on le clôt (rattrapage inclus),
- s'il n'existe pas déjà de vote pour le mois courant et qu'il y a des
  propositions → on en ouvre un.

Idempotent : relancer le même jour ne crée ni ne clôt rien de plus.
"""

from calendar import monthrange
from datetime import date

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from clubs.models import Ballot, Club, Proposition, Vote


def _next_month_bounds(first_of_month: date) -> tuple[date, date]:
    y, m = first_of_month.year, first_of_month.month
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return date(y, m, 1), date(y, m, monthrange(y, m)[1])


def _close(vote: Vote) -> None:
    start, end = _next_month_bounds(vote.cycle_month)
    winner = (
        Ballot.objects.filter(vote=vote)
        .values("proposition_id")
        .annotate(n=Count("id"))
        .order_by("-n", "proposition_id")
        .first()
    )
    vote.start_date = start
    vote.end_date = end
    if winner is not None:
        vote.winner_id = winner["proposition_id"]
        Proposition.objects.filter(club=vote.club).exclude(pk=vote.winner_id).delete()
    vote.closed_at = timezone.now()
    vote.save()


class Command(BaseCommand):
    help = "Ouvre/clôt les votes mensuels des clubs (rattrapage si jours sautés)."

    def add_arguments(self, parser):
        parser.add_argument("--today", help="ISO date (YYYY-MM-DD) pour injection en test")

    def handle(self, *args, **opts):
        today = (
            date.fromisoformat(opts["today"]) if opts.get("today") else timezone.localdate()
        )
        cm = date(today.year, today.month, 1)
        opened = closed = 0
        for club in Club.objects.all():
            open_vote = Vote.objects.filter(club=club, closed_at__isnull=True).first()
            if open_vote is not None and open_vote.cycle_month < cm:
                _close(open_vote)
                open_vote = None
                closed += 1
            if (
                open_vote is None
                and not Vote.objects.filter(club=club, cycle_month=cm).exists()
                and club.propositions.exists()
            ):
                Vote.objects.create(club=club, cycle_month=cm)
                opened += 1
        self.stdout.write(f"cycle_tick {today}: ouverts={opened} clos={closed}")
