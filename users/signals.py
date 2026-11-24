import logging

from allauth.account.signals import user_signed_up
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

log = logging.getLogger(__name__)


def _client_ip(request):
    """IP du client réel derrière Cloudflare → Caddy.

    Cloudflare pose CF-Connecting-IP avec l'IP d'origine ; sans Cloudflare
    on retombe sur la première entrée de X-Forwarded-For (celle du client,
    les proxies ajoutent la leur en fin).
    """
    if request is None:
        return None
    cf = request.META.get("HTTP_CF_CONNECTING_IP", "").strip()
    if cf:
        return cf
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


@receiver(user_logged_in)
def _on_login(sender, request, user, **_):
    ip = _client_ip(request)
    log.warning("login ip=%s user=%s", ip, user.email)
    if ip and user.last_ip != ip:
        user.last_ip = ip
        user.save(update_fields=["last_ip"])


@receiver(user_signed_up)
def _on_signup(sender, request, user, **_):
    ip = _client_ip(request)
    log.warning("signup ip=%s user=%s", ip, user.email)
    if ip:
        user.last_ip = ip
        user.save(update_fields=["last_ip"])
