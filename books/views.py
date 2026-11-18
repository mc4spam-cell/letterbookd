from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from . import openlibrary
from .models import Book


@login_required
def search(request):
    q = (request.GET.get("q") or "").strip()
    results = openlibrary.search(q) if q else []
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
    return redirect("books_detail", book_id=book.pk)


@login_required
def detail(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    if not book.description or not book.cover_id:
        book.hydrate_from_openlibrary()
    return render(request, "books/detail.html", {"book": book})
