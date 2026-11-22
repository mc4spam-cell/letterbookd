import logging

from allauth.account.signals import user_signed_up
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

log = logging.getLogger(__name__)


def _client_ip(request):
    if request is None:
        return None
    for h in ("HTTP_CF_CONNECTING_IP", "HTTP_X_REAL_IP", "HTTP_X_FORWARDED_FOR"):
        v = request.META.get(h, "")
        if v:
            return v.split(",")[0].strip()
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
