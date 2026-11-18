"""Lectures, avis, commentaires, notifications."""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class ReadingStatus(models.TextChoices):
    TO_READ = "to_read", _("à lire")
    READING = "reading", _("en cours")
    READ = "read", _("lu")
    ABANDONED = "abandoned", _("abandonné")


class Reading(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE)
    status = models.CharField(
        _("statut"), max_length=12, choices=ReadingStatus.choices, default=ReadingStatus.READ
    )
    rating = models.PositiveSmallIntegerField(
        _("note (demi-points, 0 à 10)"), null=True, blank=True
    )  # 0..10 = 0..5 étoiles par pas de 0,5
    started_on = models.DateField(_("commencé le"), null=True, blank=True)
    finished_on = models.DateField(_("terminé le"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(rating__isnull=True) | (Q(rating__gte=0) & Q(rating__lte=10)),
                name="reading_rating_range",
            )
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} — {self.book} ({self.status})"


class Review(models.Model):
    reading = models.OneToOneField(Reading, on_delete=models.CASCADE, related_name="review")
    text = models.TextField(_("avis"))
    spoiler = models.BooleanField(_("contient des spoilers"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"avis de {self.reading.user} sur {self.reading.book}"

    @property
    def author(self):
        return self.reading.user

    @property
    def book(self):
        return self.reading.book


class Comment(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} → {self.review_id}"


class Notification(models.Model):
    class Kind(models.TextChoices):
        COMMENT = "comment", _("Nouveau commentaire sur ton avis")
        REPLY = "reply", _("Nouvelle réponse à ton commentaire")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} → {self.recipient}"
