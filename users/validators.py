import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MAX_SHARED_RUN = 7


class CharacterClassesValidator:
    """Exige minuscule, majuscule, chiffre et caractère spécial."""

    def validate(self, password, user=None):
        missing = []
        if not re.search(r"[a-z]", password):
            missing.append(_("des minuscules"))
        if not re.search(r"[A-Z]", password):
            missing.append(_("des majuscules"))
        if not re.search(r"\d", password):
            missing.append(_("des chiffres"))
        if not re.search(r"[^A-Za-z0-9]", password):
            missing.append(_("des caractères spéciaux"))
        if missing:
            items = ", ".join(str(m) for m in missing)
            raise ValidationError(
                _("Le mot de passe doit contenir %(items)s.") % {"items": items},
                code="password_character_classes",
            )

    def get_help_text(self):
        return _(
            "Votre mot de passe doit contenir à la fois des minuscules, "
            "des majuscules, des chiffres et des caractères spéciaux."
        )


def shares_run(a: str, b: str, n: int) -> bool:
    """True si a et b partagent une sous-chaîne de longueur > n (case-insensitive)."""
    a, b = a.lower(), b.lower()
    size = n + 1
    return any(a[i:i + size] in b for i in range(len(a) - n))


class ConsecutiveSubstringValidator:
    """Rejette un mdp partageant >max_run car. consécutifs avec un attribut user."""

    LABELS = {
        "email": _("votre adresse e-mail"),
        "display_name": _("votre nom de membre"),
    }

    def __init__(self, max_run=MAX_SHARED_RUN, user_attributes=("email", "display_name")):
        self.max_run = max_run
        self.user_attributes = user_attributes

    def validate(self, password, user=None):
        if user is None:
            return
        for attr in self.user_attributes:
            val = getattr(user, attr, None) or ""
            if val and shares_run(val, password, self.max_run):
                raise ValidationError(
                    _("Le mot de passe reprend plus de %(n)d caractères "
                      "consécutifs de %(attr)s.")
                    % {"n": self.max_run, "attr": self.LABELS.get(attr, attr)},
                    code="password_shares_user_attr",
                )

    def get_help_text(self):
        return _(
            "Votre mot de passe ne peut reprendre plus de %(n)d caractères "
            "consécutifs de votre adresse e-mail et/ou de votre nom de membre."
        ) % {"n": self.max_run}


class PreviousPasswordRuleValidator:
    """Noop : affiche seulement la règle. Enforcée dans ChangePasswordForm."""

    def __init__(self, max_run=MAX_SHARED_RUN):
        self.max_run = max_run

    def validate(self, password, user=None):
        return

    def get_help_text(self):
        return _(
            "Votre mot de passe ne peut reprendre plus de %(n)d caractères "
            "consécutifs de votre mot de passe précédent."
        ) % {"n": self.max_run}
