from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from books.models import Book

from .models import ListItem, ReadingList
from .visibility import visible_lists


@login_required
def lists_index(request):
    my_lists = (
        ReadingList.objects.filter(owner=request.user)
        .order_by("-updated_at")
        .prefetch_related("items__book")
    )
    from .models import Reading
    my_ratings = dict(
        Reading.objects.filter(user=request.user, rating__isnull=False)
        .values_list("book_id", "rating")
    )
    for l in my_lists:
        for it in l.items.all():
            it.my_rating = my_ratings.get(it.book_id)
    all_readings = (
        Reading.objects.filter(user=request.user)
        .select_related("book")
        .order_by("-updated_at")
    )
    for rd in all_readings:
        rd.my_rating = rd.rating
    return render(
        request,
        "clubs/lists_index.html",
        {"lists": my_lists, "all_readings": all_readings},
    )


@login_required
def list_create(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()[:120]
        if name:
            rl = ReadingList.objects.create(
                owner=request.user,
                name=name,
                description=(request.POST.get("description") or "").strip(),
            )
            return redirect("list_detail", list_id=rl.pk)
    return render(request, "clubs/list_form.html", {})


@login_required
def list_detail(request, list_id):
    rl = get_object_or_404(ReadingList.objects.select_related("owner"), pk=list_id)
    if rl not in visible_lists(request.user):
        raise Http404
    items = rl.items.select_related("book")
    return render(
        request,
        "clubs/list_detail.html",
        {
            "list": rl,
            "items": items,
            "is_owner": rl.owner_id == request.user.pk,
        },
    )


@login_required
def list_remove(request, list_id, item_id):
    rl = get_object_or_404(ReadingList, pk=list_id, owner=request.user)
    if request.method == "POST":
        ListItem.objects.filter(pk=item_id, list=rl).delete()
    return redirect("list_detail", list_id=rl.pk)


@login_required
def book_add_to_list(request, book_id):
    """Ajoute un livre à une liste (existante) ou à une nouvelle liste."""
    book = get_object_or_404(Book, pk=book_id)
    my_lists = ReadingList.objects.filter(owner=request.user).order_by("name")
    if request.method == "POST":
        new_name = (request.POST.get("new_list_name") or "").strip()[:120]
        if new_name:
            rl = ReadingList.objects.create(owner=request.user, name=new_name)
        else:
            list_id = request.POST.get("list_id")
            rl = get_object_or_404(ReadingList, pk=list_id, owner=request.user)
        ListItem.objects.get_or_create(list=rl, book=book)
        rl.save(update_fields=["updated_at"])
        return redirect("list_detail", list_id=rl.pk)
    return render(
        request,
        "clubs/book_add_to_list.html",
        {"book": book, "my_lists": my_lists},
    )


@login_required
def list_delete(request, list_id):
    rl = get_object_or_404(ReadingList, pk=list_id, owner=request.user)
    if request.method == "POST":
        rl.delete()
        return redirect("lists_index")
    return redirect("list_detail", list_id=rl.pk)
