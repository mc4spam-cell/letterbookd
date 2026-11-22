from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from clubs.models import Comment, Reading, ReviewReaction

from . import openlibrary
from .models import Book


@login_required
def search(request):
    q = (request.GET.get("q") or "").strip()
    results = openlibrary.search(q) if q else []
    if results:
        olids = [r["olid"] for r in results if r.get("olid")]
        ratings = dict(
            Reading.objects.filter(
                user=request.user, book__olid__in=olids, rating__isnull=False
            ).values_list("book__olid", "rating")
        )
        for r in results:
            r["rating"] = ratings.get(r.get("olid"))
    return render(request, "books/search.html", {"q": q, "results": results})


@login_required
def add(request):
    # shortcut: on fait confiance aux champs postés depuis la page de recherche
    # (membres authentifiés d'un club privé). À durcir si l'app s'ouvre au-delà.
    if request.method != "POST":
        return redirect("books_search")
    olid = (request.POST.get("olid") or "").strip()
    if not olid:
        return redirect("books_search")
    pages = request.POST.get("pages") or None
    year = request.POST.get("year") or None
    cover_id = request.POST.get("cover_id") or None
    book, created = Book.objects.get_or_create(
        olid=olid,
        defaults={
            "title": (request.POST.get("title") or "")[:500],
            "authors": (request.POST.get("authors") or "")[:500],
            "isbn": (request.POST.get("isbn") or "")[:20],
            "pages": int(pages) if pages and pages.isdigit() else None,
            "cover_id": int(cover_id) if cover_id and cover_id.isdigit() else None,
            "year": int(year) if year and year.isdigit() else None,
        },
    )
    if created:
        book.hydrate_from_openlibrary()
    nxt = request.POST.get("next") or "detail"
    if nxt == "inline_rate":
        rating_raw = (request.POST.get("rating") or "").strip()
        rating = (
            int(rating_raw)
            if rating_raw.isdigit() and 0 <= int(rating_raw) <= 10
            else None
        )
        reading = (
            Reading.objects.filter(user=request.user, book=book)
            .order_by("-updated_at")
            .first()
        )
        if reading is None:
            Reading.objects.create(
                user=request.user, book=book, status="read", rating=rating
            )
        else:
            reading.rating = rating
            reading.save(update_fields=["rating", "updated_at"])
        return JsonResponse({"book_id": book.pk, "rating": rating})
    if nxt == "rate":
        return redirect("read_book", book_id=book.pk)
    if nxt == "list":
        return redirect("book_add_to_list", book_id=book.pk)
    return redirect("books_detail", book_id=book.pk)


@login_required
def detail(request, book_id):
    from django.db.models import Avg, Count, Q

    book = get_object_or_404(Book, pk=book_id)
    if not book.description or not book.cover_id:
        book.hydrate_from_openlibrary()

    rated = Reading.objects.filter(book=book, rating__isnull=False)
    agg = rated.aggregate(avg=Avg("rating"), total=Count("id"))
    counts = dict(rated.values_list("rating").annotate(c=Count("id")).values_list("rating", "c"))
    max_count = max(counts.values(), default=0)
    distribution = [(v, counts.get(v, 0)) for v in range(10, 0, -1)]
    avg_int = round(agg["avg"]) if agg["avg"] is not None else None

    entries = list(
        Reading.objects.filter(book=book)
        .filter(Q(rating__isnull=False) | Q(review__isnull=False))
        .select_related("user", "review")
        .order_by("-updated_at")
    )
    # Pour chaque Review visible, compter les réactions et repérer la mienne.
    review_ids = [e.review.pk for e in entries if getattr(e, "review", None)]
    my_reactions = dict(
        ReviewReaction.objects.filter(
            user=request.user, review_id__in=review_ids
        ).values_list("review_id", "kind")
    )
    counts_rows = (
        ReviewReaction.objects.filter(review_id__in=review_ids)
        .values("review_id", "kind")
        .annotate(n=Count("id"))
    )
    counts_by_review = {}
    for row in counts_rows:
        counts_by_review.setdefault(row["review_id"], {})[row["kind"]] = row["n"]
    comments_by_review = {}
    for c in (
        Comment.objects.filter(review_id__in=review_ids)
        .select_related("author")
        .order_by("created_at")
    ):
        comments_by_review.setdefault(c.review_id, []).append(c)
    my_entry = None
    other_entries = []
    for e in entries:
        e.is_mine = e.user_id == request.user.pk
        if getattr(e, "review", None):
            e.my_reaction = my_reactions.get(e.review.pk)
            e.reaction_counts = counts_by_review.get(e.review.pk, {})
            e.comments_list = comments_by_review.get(e.review.pk, [])
        if e.is_mine:
            my_entry = e
        else:
            other_entries.append(e)

    highlighted = request.GET.get("avis")
    highlighted_id = int(highlighted) if highlighted and highlighted.isdigit() else None
    if highlighted_id is not None:
        other_entries.sort(
            key=lambda e: 0 if getattr(e, "review", None) and e.review.pk == highlighted_id else 1
        )

    return render(
        request,
        "books/detail.html",
        {
            "book": book,
            "stats": agg,
            "avg_int": avg_int,
            "distribution": distribution,
            "max_count": max_count,
            "my_entry": my_entry,
            "other_entries": other_entries,
            "highlighted_review_id": highlighted_id,
        },
    )
