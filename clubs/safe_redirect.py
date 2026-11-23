from django.utils.http import url_has_allowed_host_and_scheme


def safe_back(request, fallback: str) -> str:
    """Référer HTTP si c'est bien le même site, sinon la cible de repli."""
    ref = request.META.get("HTTP_REFERER") or ""
    if ref and url_has_allowed_host_and_scheme(
        ref, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return ref
    return fallback
