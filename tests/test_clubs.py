import pytest
from django.test import Client
from django.urls import reverse

from clubs.models import Club, Membership, Role


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_create_club_makes_creator_host(make_user):
    u = make_user()
    c = _login(u)
    r = c.post(reverse("club_create"), {"name": "Mon club", "description": ""})
    club = Club.objects.get(name="Mon club")
    assert r.status_code == 302
    m = Membership.objects.get(user=u, club=club)
    assert m.role == Role.HOST


@pytest.mark.django_db
def test_join_by_token_adds_membership(make_user, make_club):
    host = make_user()
    newcomer = make_user()
    club = make_club(host)
    c = _login(newcomer)
    r = c.get(reverse("join_by_token", args=[club.invite_token]))
    assert r.status_code == 302
    assert Membership.objects.filter(user=newcomer, club=club).exists()


@pytest.mark.django_db
def test_rotate_invite_invalidates_old_token(make_user, make_club):
    host = make_user()
    newcomer = make_user()
    club = make_club(host)
    old = club.invite_token
    _login(host).post(reverse("club_settings", args=[club.pk]), {"action": "rotate"})
    club.refresh_from_db()
    assert club.invite_token != old
    r = _login(newcomer).get(reverse("join_by_token", args=[old]))
    assert r.status_code == 404


@pytest.mark.django_db
def test_host_can_exclude_member(make_user, make_club):
    host = make_user()
    member = make_user()
    club = make_club(host)
    Membership.objects.create(user=member, club=club, role=Role.MEMBER)
    _login(host).post(
        reverse("club_settings", args=[club.pk]),
        {"action": "exclude", "user_id": member.pk},
    )
    assert not Membership.objects.filter(user=member, club=club).exists()


@pytest.mark.django_db
def test_member_cannot_access_settings(make_user, make_club):
    host = make_user()
    member = make_user()
    club = make_club(host)
    Membership.objects.create(user=member, club=club, role=Role.MEMBER)
    r = _login(member).get(reverse("club_settings", args=[club.pk]))
    assert r.status_code == 404


@pytest.mark.django_db
def test_non_member_cannot_see_club(make_user, make_club):
    host = make_user()
    outsider = make_user()
    club = make_club(host)
    r = _login(outsider).get(reverse("club_detail", args=[club.pk]))
    assert r.status_code == 404


@pytest.mark.django_db
def test_profile_hidden_from_strangers(make_user, make_club):
    a = make_user()
    b = make_user()
    make_club(a)
    make_club(b)
    r = _login(a).get(reverse("profile_detail", args=[b.pk]))
    assert r.status_code == 404


@pytest.mark.django_db
def test_profile_visible_within_shared_club(make_user, make_club):
    a = make_user()
    b = make_user()
    club = make_club(a)
    Membership.objects.create(user=b, club=club, role=Role.MEMBER)
    r = _login(a).get(reverse("profile_detail", args=[b.pk]))
    assert r.status_code == 200


@pytest.mark.django_db
def test_delete_account_removes_memberships(make_user, make_club):
    host = make_user()
    cohost = make_user()
    club = make_club(host)
    Membership.objects.create(user=cohost, club=club, role=Role.HOST)
    _login(host).post(reverse("me_settings"), {"action": "delete"})
    assert Membership.objects.filter(user__pk=host.pk).count() == 0


@pytest.mark.django_db
def test_home_requires_login():
    r = Client().get(reverse("home"))
    assert r.status_code in (301, 302)
