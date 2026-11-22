from allauth.account.forms import (
    ChangePasswordForm as AllauthChangePasswordForm,
)
from allauth.account.forms import SignupForm as AllauthSignupForm
from django import forms
from django.contrib.auth.password_validation import password_validators_help_texts
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from users.validators import MAX_SHARED_RUN, shares_run


def _password_rules_html():
    lines = "<br>".join(f"&bull; {t}" for t in password_validators_help_texts())
    return mark_safe(
        '<small style="display:block;font-weight:normal;margin:6px 0;'
        f'color:var(--muted);">{lines}</small>'
    )


def _move_rules_into_label(form):
    """Affiche les règles entre le label « Mot de passe » et le champ."""
    f = form.fields.get("password1")
    if f is None:
        return
    f.help_text = ""
    f.label = mark_safe(f"{f.label}{_password_rules_html()}")


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _move_rules_into_label(self)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _move_rules_into_label(self)

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
