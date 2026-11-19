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


def _signup(email="new@example.com", password="motdepasselong123"):
    c = Client(enforce_csrf_checks=False)
    return c, c.post(
        reverse("account_signup"),
        {"email": email, "password1": password, "password2": password},
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
            "password1": "motdepasselong123",
            "password2": "motdepasselong123",
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
def test_create_invitation_requires_email_and_sends_mail(make_user, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    from django.core import mail
    u = make_user()
    c = Client()
    c.force_login(u)
    # Sans e-mail : rien n'est créé
    c.post(reverse("invites"))
    assert Invitation.objects.filter(created_by=u).count() == 0
    # Avec e-mail : création + mail
    r = c.post(reverse("invites"), {"email": "nouveau@example.com"})
    assert r.status_code == 302
    inv = Invitation.objects.get(created_by=u)
    assert inv.email == "nouveau@example.com"
    assert len(mail.outbox) == 1
    assert "nouveau@example.com" in mail.outbox[0].to
    assert inv.token in mail.outbox[0].body
