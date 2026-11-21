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


def _signup(email="new@example.com", password="Motdepasselongvalide123!", display_name=None):
    c = Client(enforce_csrf_checks=False)
    name = display_name or email.split("@")[0]
    return c, c.post(
        reverse("account_signup"),
        {
            "email": email,
            "password1": password,
            "password2": password,
            "display_name": name,
        },
    )


@pytest.mark.django_db
def test_first_user_can_signup_without_token():
    assert get_user_model().objects.count() == 0
    _, r = _signup()
    assert get_user_model().objects.filter(email="new@example.com").exists()


@pytest.mark.django_db
def test_second_signup_blocked_without_invitation(make_user):
    make_user()
    _, r = _signup(email="autre@example.com")
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
            "password1": "Motdepasselongvalide123!",
            "password2": "Motdepasselongvalide123!",
            "display_name": "nouveau",
        },
    )
    u = get_user_model().objects.filter(email="nouveau@example.com").first()
    assert u is not None
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
