"""Signup fermé sauf invitation — le premier utilisateur fonde la communauté."""

from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
from django.utils import timezone


class InvitationOnlyAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        if not get_user_model().objects.exists():
            return True
        return bool(request.session.get("invitation_token"))

    def save_user(self, request, user, form, commit=True):
        from .models import Invitation

        user = super().save_user(request, user, form, commit=commit)
        token = request.session.pop("invitation_token", None)
        if token:
            Invitation.objects.filter(token=token, used_at__isnull=True).update(
                used_at=timezone.now(), used_by=user
            )
        return user
