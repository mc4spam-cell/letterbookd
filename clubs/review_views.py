from datetime import date as _date

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from books.models import Book

from .models import Comment, Notification, Reading, ReadingStatus, Review, ReviewReaction
from .visibility import followed_ids, visible_reviews


def _parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return _date.fromisoformat(raw)
    except ValueError:
        return None


@login_required
def read_book(request, book_id):
    """Marque la lecture (statut + note + dates) et, si texte, crée/édite l'avis.

    `?nouvelle=1` force une nouvelle lecture (relecture) plutôt que de mettre
    à jour la plus récente.
    """
    book = get_object_or_404(Book, pk=book_id)
    force_new = request.GET.get("nouvelle") == "1" or request.POST.get("nouvelle") == "1"
    reading = (
        None
        if force_new
        else Reading.objects.filter(user=request.user, book=book)
        .order_by("-updated_at")
        .first()
    )
    if request.method == "POST":
        status = request.POST.get("status") or ReadingStatus.READ
        if status not in ReadingStatus.values:
            status = ReadingStatus.READ
        rating_raw = (request.POST.get("rating") or "").strip()
        rating = int(rating_raw) if rating_raw.isdigit() and 0 <= int(rating_raw) <= 10 else None
        started_on = _parse_date(request.POST.get("started_on"))
        finished_on = _parse_date(request.POST.get("finished_on"))
        if reading is None:
            reading = Reading.objects.create(
                user=request.user,
                book=book,
                status=status,
                rating=rating,
                started_on=started_on,
                finished_on=finished_on,
            )
        else:
            reading.status = status
            reading.rating = rating
            reading.started_on = started_on
            reading.finished_on = finished_on
            reading.save()
        text = (request.POST.get("review_text") or "").strip()
        spoiler = request.POST.get("spoiler") == "on"
        if text:
            Review.objects.update_or_create(
                reading=reading, defaults={"text": text, "spoiler": spoiler}
            )
        elif hasattr(reading, "review"):
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
            "force_new": force_new,
        },
    )


@login_required
def review_detail(request, review_id):
    """L'avis est affiche sur la fiche livre. On n'a plus de page dediee :
    on y redirige, en epinglant l'avis concerne."""
    review = get_object_or_404(
        Review.objects.select_related("reading__book"), pk=review_id
    )
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
    url = reverse("books_detail", args=[review.reading.book_id])
    return redirect(f"{url}?avis={review.pk}#avis-{review.pk}")


@login_required
def react_to_review(request, review_id):
    review = get_object_or_404(Review.objects.select_related("reading__book"), pk=review_id)
    if request.method == "POST":
        kind = request.POST.get("kind") or ""
        valid = {k for k, _ in ReviewReaction.Kind.choices}
        if kind in valid:
            existing = ReviewReaction.objects.filter(user=request.user, review=review).first()
            if existing is None:
                ReviewReaction.objects.create(user=request.user, review=review, kind=kind)
            elif existing.kind == kind:
                existing.delete()  # toggle off
            else:
                existing.kind = kind
                existing.save(update_fields=["kind"])
    return redirect(
        request.META.get("HTTP_REFERER")
        or reverse("books_detail", args=[review.reading.book_id])
    )


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
def notifications(request):
    qs = Notification.objects.filter(recipient=request.user).select_related(
        "actor", "comment__review__reading__book"
    )
    unread_ids = list(qs.filter(read_at__isnull=True).values_list("pk", flat=True))
    if unread_ids:
        Notification.objects.filter(pk__in=unread_ids).update(read_at=timezone.now())
    author_ids = followed_ids(request.user) + [request.user.pk]
    reviews = (
        visible_reviews(request.user)
        .filter(reading__user_id__in=author_ids)
        .select_related("reading__user", "reading__book")
        .order_by("-created_at")[:50]
    )
    return render(
        request,
        "clubs/notifications.html",
        {"notifications": qs[:100], "reviews": reviews},
    )


@login_required
def stats(request):
    qs = Reading.objects.filter(user=request.user)
    by_status = dict(qs.values_list("status").annotate(n=Count("id")))
    year = timezone.now().year
    return render(
        request,
        "clubs/stats.html",
        {
            "total": qs.count(),
            "by_status": [
                (label, by_status.get(v, 0)) for v, label in ReadingStatus.choices
            ],
            "avg_rating": qs.exclude(rating__isnull=True).aggregate(a=Avg("rating"))["a"],
            "finished_this_year": qs.filter(finished_on__year=year).count(),
            "year": year,
        },
    )


@login_required
def profile_readings(request, user_id):
    other = get_object_or_404(get_user_model(), pk=user_id)
    qs = Reading.objects.filter(user=other).select_related("book")
    status = request.GET.get("status")
    if status in ReadingStatus.values:
        qs = qs.filter(status=status)
    sort = request.GET.get("tri") or "date"
    if sort == "note":
        qs = qs.order_by("-rating", "-updated_at")
    elif sort == "auteur":
        qs = qs.order_by("book__authors", "book__title")
    elif sort == "fini":
        qs = qs.order_by("-finished_on", "-updated_at")
    else:
        sort = "date"
        qs = qs.order_by("-updated_at")
    return render(
        request,
        "clubs/readings.html",
        {
            "profile_user": other,
            "readings": qs,
            "statuses": ReadingStatus.choices,
            "current_status": status or "",
            "current_sort": sort,
        },
    )
