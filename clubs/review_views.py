from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from books.models import Book

from .models import Comment, Notification, Reading, ReadingStatus, Review
from .visibility import shares_club_with, visible_reviews, visible_users


@login_required
def read_book(request, book_id):
    """Marque la lecture (statut + note) et, si texte, crée/édite l'avis."""
    book = get_object_or_404(Book, pk=book_id)
    reading = Reading.objects.filter(user=request.user, book=book).first()
    if request.method == "POST":
        status = request.POST.get("status") or ReadingStatus.READ
        if status not in ReadingStatus.values:
            status = ReadingStatus.READ
        rating_raw = (request.POST.get("rating") or "").strip()
        rating = int(rating_raw) if rating_raw.isdigit() and 0 <= int(rating_raw) <= 10 else None
        if reading is None:
            reading = Reading.objects.create(
                user=request.user, book=book, status=status, rating=rating
            )
        else:
            reading.status = status
            reading.rating = rating
            reading.save()
        text = (request.POST.get("review_text") or "").strip()
        spoiler = request.POST.get("spoiler") == "on"
        if text:
            Review.objects.update_or_create(
                reading=reading, defaults={"text": text, "spoiler": spoiler}
            )
        elif hasattr(reading, "review"):
            # Texte vidé : on retire l'avis, pas la note.
            reading.review.delete()
        return redirect("books_detail", book_id=book.pk)
    return render(
        request,
        "clubs/read_book.html",
        {
            "book": book,
            "reading": reading,
            "review": getattr(reading, "review", None) if reading else None,
            "statuses": ReadingStatus.choices,
        },
    )


def _can_see_review(viewer, review) -> bool:
    return shares_club_with(viewer, review.reading.user)


@login_required
def review_detail(request, review_id):
    review = get_object_or_404(
        Review.objects.select_related("reading__user", "reading__book"), pk=review_id
    )
    if not _can_see_review(request.user, review):
        raise Http404
    if request.method == "POST":
        text = (request.POST.get("text") or "").strip()
        parent_id = request.POST.get("parent_id") or None
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id, review=review)
        if text:
            comment = Comment.objects.create(
                review=review, parent=parent, author=request.user, text=text
            )
            _notify_for_comment(comment)
        return redirect("review_detail", review_id=review.pk)
    replies_qs = Comment.objects.select_related("author").order_by("created_at")
    roots = (
        review.comments.filter(parent__isnull=True)
        .prefetch_related(Prefetch("replies", queryset=replies_qs))
        .select_related("author")
    )
    return render(request, "clubs/review_detail.html", {"review": review, "roots": roots})


def _notify_for_comment(comment: Comment) -> None:
    if comment.parent is not None:
        target = comment.parent.author
        kind = Notification.Kind.REPLY
    else:
        target = comment.review.reading.user
        kind = Notification.Kind.COMMENT
    if target == comment.author:
        return
    Notification.objects.create(
        recipient=target, actor=comment.author, kind=kind, comment=comment
    )


@login_required
def feed(request):
    reviews = (
        visible_reviews(request.user)
        .select_related("reading__user", "reading__book")
        .order_by("-created_at")[:50]
    )
    return render(request, "clubs/feed.html", {"reviews": reviews})


@login_required
def notifications(request):
    qs = Notification.objects.filter(recipient=request.user).select_related(
        "actor", "comment__review__reading__book"
    )
    unread = list(qs.filter(read_at__isnull=True))
    # Marque comme lus à l'affichage.
    if unread:
        Notification.objects.filter(pk__in=[n.pk for n in unread]).update(
            read_at=timezone.now()
        )
    return render(
        request, "clubs/notifications.html", {"notifications": qs[:100], "fresh": unread}
    )


@login_required
def profile_readings(request, user_id):
    from django.contrib.auth import get_user_model

    other = get_object_or_404(get_user_model(), pk=user_id)
    if other.pk != request.user.pk and other not in visible_users(request.user):
        raise Http404
    readings = (
        Reading.objects.filter(user=other).select_related("book").order_by("-updated_at")
    )
    return render(request, "clubs/readings.html", {"profile_user": other, "readings": readings})
