"""Cycle du club : proposition → vote → livre du mois.

Pas de table Sélection : un Vote clôturé avec `winner` et `start_date`/
`end_date` *est* la sélection.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import Club


class Proposition(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="propositions")
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE)
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["club", "book"], name="uniq_club_book_prop"),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.book} proposé pour {self.club}"


class Vote(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="votes")
    # Toujours le 1er du mois : un vote = le cycle d'un mois civil.
    cycle_month = models.DateField()
    closed_at = models.DateTimeField(null=True, blank=True)
    winner = models.ForeignKey(
        Proposition, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    start_date = models.DateField(_("début de lecture"), null=True, blank=True)
    end_date = models.DateField(_("fin de lecture"), null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["club"],
                condition=Q(closed_at__isnull=True),
                name="uniq_open_vote_per_club",
            ),
            models.UniqueConstraint(
                fields=["club", "cycle_month"], name="uniq_cycle_month_per_club"
            ),
        ]
        ordering = ["-cycle_month"]

    def __str__(self):
        return f"Vote {self.club} ({self.cycle_month:%Y-%m})"

    @property
    def is_open(self) -> bool:
        return self.closed_at is None


