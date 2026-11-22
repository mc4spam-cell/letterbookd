from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from books.models import Book

from .models import ListItem, Reading, ReadingList


def ensure_default_lists(user):
    ReadingList.objects.get_or_create(
        owner=user, kind=ReadingList.Kind.FAVORITES, defaults={"name": "Favoris"}
    )
    ReadingList.objects.get_or_create(
        owner=user, kind=ReadingList.Kind.TOREAD, defaults={"name": "À lire"}
    )


def _ordered_user_lists(user):
    ensure_default_lists(user)
    qs = ReadingList.objects.filter(owner=user).prefetch_related("items__book")
    fav = qs.filter(kind=ReadingList.Kind.FAVORITES).first()
    toread = qs.filter(kind=ReadingList.Kind.TOREAD).first()
    normals = list(qs.filter(kind=ReadingList.Kind.NORMAL).order_by("created_at"))
    return [l for l in [fav, toread, *normals] if l]


@login_required
def lists_index(request):
    my_lists = _ordered_user_lists(request.user)
    from .models import Reading
    my_ratings = dict(
        Reading.objects.filter(user=request.user, rating__isnull=False)
        .values_list("book_id", "rating")
    )
    fav_book_ids = set(
        ListItem.objects.filter(
            list__owner=request.user, list__kind=ReadingList.Kind.FAVORITES
        ).values_list("book_id", flat=True)
    )
    for rl in my_lists:
        for it in rl.items.all():
            it.my_rating = my_ratings.get(it.book_id)
            it.is_favorite = it.book_id in fav_book_ids
    all_readings = (
        Reading.objects.filter(user=request.user)
        .select_related("book")
        .order_by("-updated_at")
    )
    for rd in all_readings:
        rd.my_rating = rd.rating
        rd.is_favorite = rd.book_id in fav_book_ids
    return render(
        request,
        "clubs/lists_index.html",
        {
            "lists": my_lists,
            "all_readings": all_readings,
            "add_to_list_lists": ReadingList.objects.filter(owner=request.user)
                .exclude(kind=ReadingList.Kind.FAVORITES)
                .annotate(items_count=Count("items")).order_by("name"),
        },
    )


@login_required
def list_create(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()[:120]
        if name:
            ReadingList.objects.create(
                owner=request.user,
                name=name,
                description=(request.POST.get("description") or "").strip(),
            )
            return redirect("lists_index")
    return render(request, "clubs/list_form.html", {})


@login_required
def list_remove(request, list_id, item_id):
    rl = get_object_or_404(ReadingList, pk=list_id, owner=request.user)
    if request.method == "POST":
        ListItem.objects.filter(pk=item_id, list=rl).delete()
    return redirect("lists_index")


@login_required
def book_add_to_list(request, book_id):
    """Ajoute un livre à une liste, ou l'y déplace depuis une autre."""
    book = get_object_or_404(Book, pk=book_id)
    my_lists = (
        ReadingList.objects.filter(owner=request.user)
        .annotate(items_count=Count("items"))
        .order_by("name")
    )
    if request.method == "POST":
        new_name = (request.POST.get("new_list_name") or "").strip()[:120]
        if new_name:
            rl = ReadingList.objects.create(owner=request.user, name=new_name)
        else:
            list_id = request.POST.get("list_id")
            rl = get_object_or_404(ReadingList, pk=list_id, owner=request.user)
        ListItem.objects.get_or_create(list=rl, book=book)
        rl.save(update_fields=["updated_at"])
        from_list_id = request.POST.get("from_list_id")
        if from_list_id:
            ListItem.objects.filter(
                list__owner=request.user, list_id=from_list_id, book=book
            ).exclude(list=rl).delete()
        return redirect("lists_index")
    return render(
        request,
        "clubs/book_add_to_list.html",
        {"book": book, "my_lists": my_lists},
    )


@login_required
def reading_delete(request, reading_id):
    if request.method == "POST":
        Reading.objects.filter(pk=reading_id, user=request.user).delete()
    return redirect("lists_index")


@login_required
def list_delete(request, list_id):
    rl = get_object_or_404(ReadingList, pk=list_id, owner=request.user)
    if request.method == "POST" and rl.kind == ReadingList.Kind.NORMAL:
        rl.delete()
    return redirect("lists_index")


@login_required
def toggle_favorite(request, book_id):
    if request.method != "POST":
        return redirect("books_detail", book_id=book_id)
    book = get_object_or_404(Book, pk=book_id)
    ensure_default_lists(request.user)
    fav = ReadingList.objects.get(
        owner=request.user, kind=ReadingList.Kind.FAVORITES
    )
    existing = ListItem.objects.filter(list=fav, book=book).first()
    if existing:
        existing.delete()
        is_fav = False
    else:
        ListItem.objects.create(list=fav, book=book)
        is_fav = True
    fav.save(update_fields=["updated_at"])
    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse({"is_favorite": is_fav})
    return redirect(
        request.META.get("HTTP_REFERER")
        or reverse("books_detail", args=[book_id])
    )
