from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.cache import patch_cache_control
from django.views.static import serve as static_serve

from .review_models import Comment, Reading, Review

staff_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff)


def _private(resp):
    # Cloudflare / any shared cache must never keep a 302-to-login response
    # and later replay it to a signed-in user.
    patch_cache_control(resp, private=True, no_store=True)
    return resp


def _serve_gated(request, path, root, needs_staff):
    if not request.user.is_authenticated:
        return _private(redirect(f"{settings.LOGIN_URL}?next={request.path}"))
    if needs_staff and not request.user.is_staff:
        return _private(redirect("home"))
    return _private(static_serve(request, path, document_root=root))


def general_doc(request, path):
    return _serve_gated(request, path, str(settings.BASE_DIR / "documentation_public"), needs_staff=False)


def moderation_doc(request, path):
    return _serve_gated(request, path, str(settings.BASE_DIR / "documentation_admin"), needs_staff=True)

PAGE_SIZE = 50

# {tab: {col: orm_field}}
SORTS = {
    "members": {
        "member": "display_name",
        "email": "email",
        "joined": "date_joined",
        "books": "nb_readings",
        "ip": "last_ip",
        "state": "state_rank",
    },
    "readings": {
        "member": "user__display_name",
        "title": "book__title",
        "date": "created_at",
    },
    "reviews": {
        "member": "reading__user__display_name",
        "title": "reading__book__title",
        "date": "created_at",
    },
    "comments": {
        "member": "author__display_name",
        "title": "review__reading__book__title",
        "date": "created_at",
    },
}


def _state_label(u):
    if u.is_deleted:
        return "supprimé"
    if not u.is_active:
        return "suspendu"
    if u.is_staff:
        return "admin"
    return "actif"


def _sort_qs(qs, tab, request):
    sort = request.GET.get("sort") or {
        "members": "joined", "readings": "date", "reviews": "date", "comments": "date"
    }[tab]
    direction = request.GET.get("dir", "desc")
    field = SORTS[tab].get(sort)
    if not field:
        return qs, sort, direction
    prefix = "" if direction == "asc" else "-"
    return qs.order_by(f"{prefix}{field}"), sort, direction


def _paginate(request, qs):
    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        page = 1
    return Paginator(qs, PAGE_SIZE).get_page(page)


def _q(request, key):
    return (request.GET.get(f"q_{key}") or "").strip()


@staff_required
def moderation(request):
    tab = request.GET.get("tab") or "members"
    if tab not in SORTS:
        tab = "members"
    User = get_user_model()
    ctx = {"tab": tab, "filters": {k: request.GET.get(f"q_{k}", "") for k in
            ["member", "email", "ip", "state", "title", "text"]}}

    if tab == "members":
        qs = User.objects.annotate(
            nb_readings=Count("reading", distinct=True),
            state_rank=Case(
                When(is_deleted=True, then=Value(4)),
                When(is_active=False, then=Value(3)),
                When(is_staff=True, then=Value(2)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        if v := _q(request, "member"):
            qs = qs.filter(display_name__icontains=v)
        if v := _q(request, "email"):
            qs = qs.filter(email__icontains=v)
        if v := _q(request, "ip"):
            qs = qs.filter(last_ip__icontains=v)
        state = _q(request, "state")
        if state == "actif":
            qs = qs.filter(is_active=True, is_staff=False, is_deleted=False)
        elif state == "admin":
            qs = qs.filter(is_staff=True, is_active=True, is_deleted=False)
        elif state == "suspendu":
            qs = qs.filter(is_active=False, is_deleted=False)
        elif state == "supprime":
            qs = qs.filter(is_deleted=True)
        qs, sort, direction = _sort_qs(qs, tab, request)
        page = _paginate(request, qs)
        for u in page.object_list:
            u.state_label = _state_label(u)
        ctx.update(page=page, sort=sort, dir=direction)

    elif tab == "readings":
        qs = Reading.objects.select_related("user", "book")
        if v := _q(request, "member"):
            qs = qs.filter(user__display_name__icontains=v)
        if v := _q(request, "title"):
            qs = qs.filter(book__title__icontains=v)
        qs, sort, direction = _sort_qs(qs, tab, request)
        ctx.update(page=_paginate(request, qs), sort=sort, dir=direction)

    elif tab == "reviews":
        qs = Review.objects.select_related("reading__user", "reading__book")
        if v := _q(request, "member"):
            qs = qs.filter(reading__user__display_name__icontains=v)
        if v := _q(request, "title"):
            qs = qs.filter(reading__book__title__icontains=v)
        if v := _q(request, "text"):
            qs = qs.filter(text__icontains=v)
        qs, sort, direction = _sort_qs(qs, tab, request)
        ctx.update(page=_paginate(request, qs), sort=sort, dir=direction)

    else:  # comments
        qs = Comment.objects.select_related("author", "review__reading__book")
        if v := _q(request, "member"):
            qs = qs.filter(author__display_name__icontains=v)
        if v := _q(request, "title"):
            qs = qs.filter(review__reading__book__title__icontains=v)
        if v := _q(request, "text"):
            qs = qs.filter(text__icontains=v)
        qs, sort, direction = _sort_qs(qs, tab, request)
        ctx.update(page=_paginate(request, qs), sort=sort, dir=direction)

    return render(request, "clubs/moderation.html", ctx)


def _action(request, user_id, action):
    User = get_user_model()
    target = get_object_or_404(User, pk=user_id)
    if target.pk == request.user.pk or target.is_superuser:
        return redirect("moderation")
    if action == "suspend":
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
    elif action == "staff":
        target.is_staff = not target.is_staff
        target.save(update_fields=["is_staff"])
    elif action == "delete":
        target.is_deleted = True
        target.is_active = False
        target.save(update_fields=["is_deleted", "is_active"])
    return redirect("moderation")


@staff_required
def moderation_user_action(request, user_id, action):
    if request.method == "POST":
        return _action(request, user_id, action)
    return redirect("moderation")


@staff_required
def moderation_delete(request, kind, obj_id):
    if request.method != "POST":
        return redirect("moderation")
    model = {"reading": Reading, "review": Review, "comment": Comment}.get(kind)
    if model:
        model.objects.filter(pk=obj_id).delete()
    return redirect("moderation")
