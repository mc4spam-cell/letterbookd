import re


def norm_name(s: str) -> str:
    """Normalise titre ou auteur pour comparaison : minuscules, sans séparateurs."""
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())
