"""Noms de prix exposés à gettext pour extraction par makemessages.

Les noms sont stockés en base en français (cf. `wikipedia.PRIZES`). L'affichage
passe par `{% translate p.prize_name %}` : le catalogue est utilisé à l'exécution.
"""

from django.utils.translation import gettext_lazy as _

PRIZE_LABELS = (
    _("Prix Goncourt"),
    _("Prix Goncourt des Lycéens"),
    _("Prix Renaudot"),
    _("Prix Femina"),
    _("Prix Médicis"),
    _("Prix Interallié"),
    _("Prix Décembre"),
    _("Grand prix du roman de l'Académie française"),
    _("Prix du Livre Inter"),
    _("Prix des Libraires"),
    _("Prix du roman Fnac"),
    _("Prix des cinq continents de la francophonie"),
)
