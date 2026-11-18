import secrets

from django.conf import settings
from django.db import models
from django.db.models import F, Q


def _new_invite_token() -> str:
    return secrets.token_urlsafe(32)


class Invitation(models.Model):
    token = models.CharField(max_length=64, unique=True, default=_new_invite_token)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invitations_sent",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invitation",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"invitation {self.token[:8]}…"

    @property
    def is_used(self) -> bool:
        return self.used_at is not None


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following_set"
    )
    followed = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers_set"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "followed"], name="uniq_follow"),
            models.CheckConstraint(condition=~Q(follower=F("followed")), name="no_self_follow"),
        ]

    def __str__(self):
        return f"{self.follower} → {self.followed}"


from .list_models import ListItem, ReadingList  # noqa: E402, F401
from .review_models import (  # noqa: E402, F401
    Comment,
    Notification,
    Reading,
    ReadingStatus,
    Review,
)
