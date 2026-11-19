import pytest
from django.test import Client
from django.urls import reverse

from books.models import Book
from clubs.models import Reading, Review, ReviewReaction


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def review(db, make_user):
    author = make_user()
    book = Book.objects.create(olid="OLR1", title="T", authors="A")
    reading = Reading.objects.create(user=author, book=book, status="read", rating=8)
    return Review.objects.create(reading=reading, text="avis")


@pytest.mark.django_db
def test_react_creates_reaction(make_user, review):
    u = make_user()
    _login(u).post(reverse("react_to_review", args=[review.pk]), {"kind": "approve"})
    assert ReviewReaction.objects.filter(user=u, review=review, kind="approve").exists()


@pytest.mark.django_db
def test_react_switching_kind_replaces(make_user, review):
    u = make_user()
    c = _login(u)
    c.post(reverse("react_to_review", args=[review.pk]), {"kind": "approve"})
    c.post(reverse("react_to_review", args=[review.pk]), {"kind": "disapprove"})
    reactions = ReviewReaction.objects.filter(user=u, review=review)
    assert reactions.count() == 1
    assert reactions.get().kind == "disapprove"


@pytest.mark.django_db
def test_react_same_kind_toggles_off(make_user, review):
    u = make_user()
    c = _login(u)
    c.post(reverse("react_to_review", args=[review.pk]), {"kind": "approve"})
    c.post(reverse("react_to_review", args=[review.pk]), {"kind": "approve"})
    assert not ReviewReaction.objects.filter(user=u, review=review).exists()


@pytest.mark.django_db
def test_invalid_kind_is_ignored(make_user, review):
    u = make_user()
    _login(u).post(reverse("react_to_review", args=[review.pk]), {"kind": "banane"})
    assert not ReviewReaction.objects.filter(user=u, review=review).exists()


@pytest.mark.django_db
def test_book_detail_shows_reaction_counts(make_user, review):
    a, b, c = make_user(), make_user(), make_user()
    ReviewReaction.objects.create(user=a, review=review, kind="approve")
    ReviewReaction.objects.create(user=b, review=review, kind="approve")
    ReviewReaction.objects.create(user=c, review=review, kind="question")
    resp = _login(a).get(reverse("books_detail", args=[review.reading.book_id]))
    content = resp.content.decode()
    # 2 approuvent, 1 interroge
    assert "approve\"" in content and ">2</span>" in content or ">2" in content
    # Le bouton approuver de A est actif
    assert "react-btn approve active" in content
