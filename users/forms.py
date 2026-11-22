from allauth.account.forms import (
    ChangePasswordForm as AllauthChangePasswordForm,
)
from allauth.account.forms import SignupForm as AllauthSignupForm
from django import forms
from django.utils.translation import gettext_lazy as _

from users.validators import MAX_SHARED_RUN, shares_run


class SignupForm(AllauthSignupForm):
    display_name = forms.CharField(
        label=_("Nom de membre"),
        max_length=80,
        required=True,
        help_text=_(
            "C'est ce nom que les autres membres verront. "
            "Les adresses e-mail restent privées."
        ),
    )

    field_order = ["display_name", "email", "password1", "password2"]

    def clean_display_name(self):
        from users.models import User
        name = self.cleaned_data["display_name"].strip()
        if not name:
            raise forms.ValidationError(_("Le nom de membre est obligatoire."))
        if User.objects.filter(display_name__iexact=name).exists():
            raise forms.ValidationError(_("Ce nom est déjà pris, choisis-en un autre."))
        return name

    def save(self, request):
        user = super().save(request)
        user.display_name = self.cleaned_data["display_name"].strip()[:80]
        user.save(update_fields=["display_name"])
        return user


class ChangePasswordForm(AllauthChangePasswordForm):
    """Ajoute la règle « mdp précédent » (allauth ne la connaît pas)."""

    def clean(self):
        cleaned = super().clean()
        old = cleaned.get("oldpassword")
        new = cleaned.get("password1")
        if old and new and shares_run(old, new, MAX_SHARED_RUN):
            raise forms.ValidationError(
                _("Le nouveau mot de passe reprend plus de %(n)d caractères "
                  "consécutifs de l'ancien.") % {"n": MAX_SHARED_RUN},
                code="password_shares_old",
            )
        return cleaned
