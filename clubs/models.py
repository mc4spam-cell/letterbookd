import secrets

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def _new_token() -> str:
    return secrets.token_urlsafe(32)


class Club(models.Model):
    name = models.CharField(_("nom"), max_length=120)
    description = models.TextField(_("description"), blank=True)
    invite_token = models.CharField(
        _("jeton d'invitation"), max_length=64, unique=True, default=_new_token
    )
    created_at = models.DateTimeField(auto_now_add=True)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Membership", related_name="clubs"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def rotate_invite(self) -> str:
        self.invite_token = _new_token()
        self.save(update_fields=["invite_token"])
        return self.invite_token


class Role(models.TextChoices):
    HOST = "host", _("animateur")
    MEMBER = "member", _("membre")


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "club"], name="uniq_user_club"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.club} ({self.role})"


from .cycle_models import Ballot, Proposition, Vote  # noqa: E402, F401
from .list_models import ListItem, ReadingList  # noqa: E402, F401
from .review_models import (  # noqa: E402, F401
    Comment,
    Notification,
    Reading,
    ReadingStatus,
    Review,
)
