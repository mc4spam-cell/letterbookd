import pytest
from django.test import Client
from django.urls import reverse

from books.models import Book
from clubs.models import Comment, Notification, Reading, Review
from clubs.visibility import visible_reviews


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def book(db):
    return Book.objects.create(olid="OL1W", title="Belle du Seigneur", authors="Cohen")


@pytest.mark.django_db
def test_rate_and_review_a_book(make_user, book):
    u = make_user()
    r = _login(u).post(
        reverse("read_book", args=[book.pk]),
        {"status": "read", "rating": "9", "review_text": "Magnifique.", "spoiler": "on"},
    )
    assert r.status_code == 302
    reading = Reading.objects.get(user=u, book=book)
    assert reading.rating == 9 and reading.status == "read"
    review = Review.objects.get(reading=reading)
    assert review.text == "Magnifique." and review.spoiler is True


@pytest.mark.django_db
def test_rating_without_review_is_allowed(make_user, book):
    u = make_user()
    _login(u).post(reverse("read_book", args=[book.pk]), {"rating": "5"})
    reading = Reading.objects.get(user=u, book=book)
    assert reading.rating == 5
    assert not Review.objects.filter(reading=reading).exists()


@pytest.mark.django_db
def test_invalid_rating_is_rejected(make_user, book):
    u = make_user()
    _login(u).post(reverse("read_book", args=[book.pk]), {"rating": "11"})
    assert Reading.objects.get(user=u, book=book).rating is None


@pytest.mark.django_db
def test_review_visible_to_any_authenticated_user(make_user, book):
    author = make_user()
    reader = make_user()
    _login(author).post(reverse("read_book", args=[book.pk]), {"review_text": "ok"})
    review = Review.objects.get()
    assert _login(reader).get(reverse("review_detail", args=[review.pk])).status_code == 200
    assert review in visible_reviews(reader)


@pytest.mark.django_db
def test_comment_and_reply_notify(make_user, book):
    author = make_user()
    mate = make_user()
    _login(author).post(reverse("read_book", args=[book.pk]), {"review_text": "ok"})
    review = Review.objects.get()

    _login(mate).post(reverse("review_detail", args=[review.pk]), {"text": "D'accord"})
    comment = Comment.objects.get()
    notif = Notification.objects.get(recipient=author)
    assert notif.kind == "comment" and notif.actor == mate and notif.comment == comment

    _login(author).post(
        reverse("review_detail", args=[review.pk]),
        {"text": "Merci", "parent_id": comment.pk},
    )
    reply_notif = Notification.objects.get(recipient=mate)
    assert reply_notif.kind == "reply" and reply_notif.actor == author


@pytest.mark.django_db
def test_self_comments_do_not_notify(make_user, book):
    author = make_user()
    _login(author).post(reverse("read_book", args=[book.pk]), {"review_text": "ok"})
    review = Review.objects.get()
    _login(author).post(reverse("review_detail", args=[review.pk]), {"text": "précision"})
    assert not Notification.objects.exists()


@pytest.mark.django_db
def test_notifications_marks_read_on_view(make_user, book):
    author = make_user()
    mate = make_user()
    _login(author).post(reverse("read_book", args=[book.pk]), {"review_text": "ok"})
    review = Review.objects.get()
    _login(mate).post(reverse("review_detail", args=[review.pk]), {"text": "hop"})
    assert Notification.objects.filter(recipient=author, read_at__isnull=True).count() == 1
    _login(author).get(reverse("notifications"))
    assert Notification.objects.filter(recipient=author, read_at__isnull=True).count() == 0


@pytest.mark.django_db
def test_clearing_review_text_removes_review_not_rating(make_user, book):
    u = make_user()
    _login(u).post(reverse("read_book", args=[book.pk]), {"rating": "7", "review_text": "aa"})
    assert Review.objects.count() == 1
    _login(u).post(reverse("read_book", args=[book.pk]), {"rating": "7", "review_text": ""})
    assert Review.objects.count() == 0
    assert Reading.objects.get(user=u, book=book).rating == 7
