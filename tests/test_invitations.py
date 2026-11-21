import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from clubs.models import Invitation


def _csrf(client, url):
    r = client.get(url)
    import re
    m = re.search(rb'name="csrfmiddlewaretoken" value="([^"]+)"', r.content)
    return m.group(1).decode() if m else ""


# Mot de passe neutre qui passe tous les validateurs (14 car., 4 classes,
# dissemblance avec l'email et le display_name).
_PWD = "Zx9!KbqmPr7Lv2n$a8Q"


def _signup(email="brandnew@example.com", password=_PWD, display_name="brandnew"):
    c = Client(enforce_csrf_checks=False)
    r = c.post(
        reverse("account_signup"),
        {
            "email": email,
            "password1": password,
            "password2": password,
            "display_name": display_name,
        },
    )
    return c, r


@pytest.mark.django_db
def test_first_user_can_signup_without_token():
    assert get_user_model().objects.count() == 0
    _, r = _signup()
    assert get_user_model().objects.filter(email="brandnew@example.com").exists()


@pytest.mark.django_db
def test_second_signup_blocked_without_invitation(make_user):
    make_user()
    _, r = _signup(email="autre@example.com", display_name="autre")
    assert not get_user_model().objects.filter(email="autre@example.com").exists()


@pytest.mark.django_db
def test_signup_with_valid_invitation(make_user):
    host = make_user()
    inv = Invitation.objects.create(created_by=host)
    c = Client()
    # suit le lien d'invitation (dépose le token en session)
    r = c.get(reverse("accept_invitation", args=[inv.token]))
    assert r.status_code == 302
    # soumet le signup
    r = c.post(
        reverse("account_signup"),
        {
            "email": "nouveau@example.com",
            "password1": _PWD,
            "password2": _PWD,
            "display_name": "membrenouveau",
        },
    )
    u = get_user_model().objects.filter(email="nouveau@example.com").first()
    assert u is not None, (
        f"signup failed, status={r.status_code} content={r.content[:400]!r}"
    )
    inv.refresh_from_db()
    assert inv.used_at is not None and inv.used_by_id == u.pk


@pytest.mark.django_db
def test_used_token_cannot_be_reused(make_user):
    host = make_user()
    inv = Invitation.objects.create(created_by=host, used_at="2026-11-19T12:00:00Z")
    r = Client().get(reverse("accept_invitation", args=[inv.token]))
    assert r.status_code == 404


@pytest.mark.django_db
def test_invalid_token_is_rejected():
    r = Client().get(reverse("accept_invitation", args=["nope"]))
    assert r.status_code == 404


@pytest.mark.django_db
def test_post_creates_invitation(make_user):
    u = make_user()
    c = Client()
    c.force_login(u)
    r = c.post(reverse("invites"))
    assert r.status_code == 302
    assert Invitation.objects.filter(created_by=u, used_at__isnull=True).count() == 1
