"""Visibilité : communauté unique, tout utilisateur authentifié voit tout
sauf les membres marqués supprimés."""

import pytest
from django.contrib.auth.models import AnonymousUser

from books.models import Book
from clubs.models import Follow, Reading, ReadingList, Review
from clubs.visibility import followed_ids, visible_lists, visible_reviews, visible_users


@pytest.mark.django_db
def test_authenticated_user_sees_everyone(make_user):
    a = make_user()
    b = make_user()
    assert b in visible_users(a)


def test_anonymous_sees_nothing():
    anon = AnonymousUser()
    assert visible_users(anon).count() == 0
    assert visible_reviews(anon).count() == 0
    assert visible_lists(anon).count() == 0


@pytest.mark.django_db
def test_deleted_user_is_invisible(make_user):
    a = make_user()
    gone = make_user()
    gone.is_deleted = True
    gone.save(update_fields=["is_deleted"])
    assert gone not in visible_users(a)
    book = Book.objects.create(olid="OL1W", title="t")
    reading = Reading.objects.create(user=gone, book=book, status="read")
    Review.objects.create(reading=reading, text="hi")
    ReadingList.objects.create(owner=gone, name="l")
    assert visible_reviews(a).count() == 0
    assert visible_lists(a).count() == 0
    Follow.objects.create(follower=a, followed=gone)
    assert followed_ids(a) == []
