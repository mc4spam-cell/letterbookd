import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class CharacterClassesValidator:
    """Exige minuscule, majuscule, chiffre et caractère spécial."""

    def validate(self, password, user=None):
        missing = []
        if not re.search(r"[a-z]", password):
            missing.append(_("une minuscule"))
        if not re.search(r"[A-Z]", password):
            missing.append(_("une majuscule"))
        if not re.search(r"\d", password):
            missing.append(_("un chiffre"))
        if not re.search(r"[^A-Za-z0-9]", password):
            missing.append(_("un caractère spécial"))
        if missing:
            raise ValidationError(
                _("Le mot de passe doit contenir %(items)s.") % {"items": ", ".join(str(m) for m in missing)},
                code="password_character_classes",
            )

    def get_help_text(self):
        return _(
            "Doit contenir au moins une minuscule, une majuscule, un chiffre et un caractère spécial."
        )
