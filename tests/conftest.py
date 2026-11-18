import pytest
from django.contrib.auth import get_user_model

from clubs.models import Follow


@pytest.fixture
def make_user(db):
    counter = {"n": 0}

    def _make(email=None, password="pw"):
        counter["n"] += 1
        email = email or f"u{counter['n']}@example.test"
        return get_user_model().objects.create_user(email=email, password=password)

    return _make


@pytest.fixture
def follow(db):
    def _follow(follower, followed):
        return Follow.objects.get_or_create(follower=follower, followed=followed)[0]

    return _follow
