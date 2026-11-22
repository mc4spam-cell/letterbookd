from allauth.account.signals import user_signed_up
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


def _client_ip(request):
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


@receiver(user_logged_in)
def _on_login(sender, request, user, **_):
    ip = _client_ip(request)
    if ip and user.last_ip != ip:
        user.last_ip = ip
        user.save(update_fields=["last_ip"])


@receiver(user_signed_up)
def _on_signup(sender, request, user, **_):
    ip = _client_ip(request)
    if ip:
        user.last_ip = ip
        user.save(update_fields=["last_ip"])
