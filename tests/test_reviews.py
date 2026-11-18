import pytest
from django.test import Client
from django.urls import reverse

from books.models import Book
from clubs.models import Comment, Membership, Notification, Reading, Review, Role
from clubs.visibility import visible_reviews


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def book(db):
    return Book.objects.create(olid="OL1W", title="Belle du Seigneur", authors="Cohen")


def _member(club, user, role=Role.MEMBER):
    Membership.objects.create(user=user, club=club, role=role)


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
def test_review_visibility_follows_shared_club(make_user, make_club, book):
    author = make_user()
    friend = make_user()
    stranger = make_user()
    club = make_club(author)
    _member(club, friend)
    # L'étranger dans un autre club
    make_club(stranger, name="autre")
    _login(author).post(reverse("read_book", args=[book.pk]), {"review_text": "ok"})
    review = Review.objects.get()

    assert _login(friend).get(reverse("review_detail", args=[review.pk])).status_code == 200
    assert _login(stranger).get(reverse("review_detail", args=[review.pk])).status_code == 404
    assert review in visible_reviews(friend)
    assert review not in visible_reviews(stranger)


@pytest.mark.django_db
def test_comment_and_reply_notify(make_user, make_club, book):
    author = make_user()
    mate = make_user()
    club = make_club(author)
    _member(club, mate)
    _login(author).post(reverse("read_book", args=[book.pk]), {"review_text": "ok"})
    review = Review.objects.get()

    # mate commente l'avis → l'auteur reçoit une notif
    _login(mate).post(reverse("review_detail", args=[review.pk]), {"text": "D'accord"})
    comment = Comment.objects.get()
    notif = Notification.objects.get(recipient=author)
    assert notif.kind == "comment" and notif.actor == mate and notif.comment == comment

    # author répond → mate reçoit une notif de réponse
    _login(author).post(
        reverse("review_detail", args=[review.pk]),
        {"text": "Merci", "parent_id": comment.pk},
    )
    reply_notif = Notification.objects.get(recipient=mate)
    assert reply_notif.kind == "reply" and reply_notif.actor == author


@pytest.mark.django_db
def test_self_comments_do_not_notify(make_user, make_club, book):
    author = make_user()
    make_club(author)
    _login(author).post(reverse("read_book", args=[book.pk]), {"review_text": "ok"})
    review = Review.objects.get()
    _login(author).post(reverse("review_detail", args=[review.pk]), {"text": "précision"})
    assert not Notification.objects.exists()


@pytest.mark.django_db
def test_feed_shows_visible_reviews_only(make_user, make_club, book):
    me = make_user()
    friend = make_user()
    stranger = make_user()
    club = make_club(me)
    _member(club, friend)
    make_club(stranger, name="autre")
    _login(friend).post(reverse("read_book", args=[book.pk]), {"review_text": "vu"})
    other_book = Book.objects.create(olid="OL2W", title="X", authors="Y")
    _login(stranger).post(reverse("read_book", args=[other_book.pk]), {"review_text": "caché"})
    r = _login(me).get(reverse("feed"))
    assert b"vu" not in r.content  # le flux liste les auteurs, pas le texte
    assert friend.email.encode() in r.content or b"@example" in r.content
    assert stranger.email.encode() not in r.content


@pytest.mark.django_db
def test_notifications_marks_read_on_view(make_user, make_club, book):
    author = make_user()
    mate = make_user()
    club = make_club(author)
    _member(club, mate)
    _login(author).post(reverse("read_book", args=[book.pk]), {"review_text": "ok"})
    review = Review.objects.get()
    _login(mate).post(reverse("review_detail", args=[review.pk]), {"text": "hop"})
    assert Notification.objects.filter(recipient=author, read_at__isnull=True).count() == 1
    _login(author).get(reverse("notifications"))
    assert Notification.objects.filter(recipient=author, read_at__isnull=True).count() == 0


@pytest.mark.django_db
def test_readings_page_hidden_from_strangers(make_user, make_club, book):
    a = make_user()
    b = make_user()
    make_club(a)
    make_club(b, name="autre")
    _login(a).post(reverse("read_book", args=[book.pk]), {"rating": "5"})
    assert _login(b).get(reverse("profile_readings", args=[a.pk])).status_code == 404


@pytest.mark.django_db
def test_clearing_review_text_removes_review_not_rating(make_user, book):
    u = make_user()
    _login(u).post(reverse("read_book", args=[book.pk]), {"rating": "7", "review_text": "aa"})
    assert Review.objects.count() == 1
    _login(u).post(reverse("read_book", args=[book.pk]), {"rating": "7", "review_text": ""})
    assert Review.objects.count() == 0
    assert Reading.objects.get(user=u, book=book).rating == 7
