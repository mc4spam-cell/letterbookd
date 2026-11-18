from django import template

register = template.Library()


def _stars(rating: int) -> str:
    rating = max(0, min(10, int(rating)))
    full, half = divmod(rating, 2)
    return "★" * full + ("½" if half else "") + "☆" * (5 - full - half)


@register.filter
def stars(rating):
    """0..10 demi-points → ★★★½☆ (vide si None)."""
    if rating is None:
        return ""
    return _stars(rating)


@register.simple_tag
def rating_choices():
    """Les 11 options (0..10) pour le picker étoiles."""
    return [(i, _stars(i)) for i in range(11)]
