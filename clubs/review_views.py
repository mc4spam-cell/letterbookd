from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from books.models import Book

from .models import Comment, Notification, Reading, ReadingStatus, Review
from .visibility import shares_club_with, visible_users


def _parse_date(raw):
    from datetime import date as _d

    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return _d.fromisoformat(raw)
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
            "force_new": force_new,
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
    from .visibility import visible_clubs

    sections = []
    for club in visible_clubs(request.user).order_by("name"):
        member_ids = club.members.values_list("id", flat=True)
        reviews = (
            Review.objects.filter(reading__user_id__in=member_ids)
            .select_related("reading__user", "reading__book")
            .order_by("-created_at")[:20]
        )
        sections.append((club, list(reviews)))
    return render(request, "clubs/feed.html", {"sections": sections})


@login_required
def notifications(request):
    from .visibility import visible_clubs

    my_notifs = Notification.objects.filter(recipient=request.user).select_related(
        "actor", "comment__review__reading__book"
    )
    unread_ids = list(my_notifs.filter(read_at__isnull=True).values_list("pk", flat=True))
    sections = []
    for club in visible_clubs(request.user).order_by("name"):
        member_ids = list(club.members.values_list("id", flat=True))
        notifs = list(my_notifs.filter(actor_id__in=member_ids).order_by("-created_at")[:50])
        sections.append((club, notifs))
    if unread_ids:
        Notification.objects.filter(pk__in=unread_ids).update(read_at=timezone.now())
    return render(request, "clubs/notifications.html", {"sections": sections})


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
    from django.contrib.auth import get_user_model

    other = get_object_or_404(get_user_model(), pk=user_id)
    if other.pk != request.user.pk and other not in visible_users(request.user):
        raise Http404
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
