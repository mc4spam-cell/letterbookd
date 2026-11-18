from django import template

register = template.Library()


@register.filter
def stars(rating):
    """0..10 demi-points → ★★★½☆ (vide si None)."""
    if rating is None:
        return ""
    rating = max(0, min(10, int(rating)))
    full, half = divmod(rating, 2)
    return "★" * full + ("½" if half else "") + "☆" * (5 - full - half)
