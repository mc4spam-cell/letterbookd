import pytest
from django.contrib.auth import get_user_model

from clubs.models import Club, Membership, Role


@pytest.fixture
def make_user(db):
    counter = {"n": 0}

    def _make(email=None, password="pw"):
        counter["n"] += 1
        email = email or f"u{counter['n']}@example.test"
        return get_user_model().objects.create_user(email=email, password=password)

    return _make


@pytest.fixture
def make_club(db):
    def _make(host, name="Club"):
        club = Club.objects.create(name=name)
        Membership.objects.create(user=host, club=club, role=Role.HOST)
        return club

    return _make
