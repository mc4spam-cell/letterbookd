from allauth.account.forms import SignupForm as AllauthSignupForm
from django import forms
from django.utils.translation import gettext_lazy as _


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
