from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .review_models import Comment, Reading, Review

staff_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff)


@staff_required
def moderation(request):
    User = get_user_model()
    users = (
        User.objects.annotate(nb_readings=Count("reading", distinct=True))
        .order_by("-date_joined")
    )
    recent_readings = Reading.objects.select_related("user", "book").order_by("-created_at")[:20]
    recent_reviews = Review.objects.select_related("reading__user", "reading__book").order_by("-created_at")[:20]
    recent_comments = Comment.objects.select_related("author", "review").order_by("-created_at")[:20]
    return render(
        request,
        "clubs/moderation.html",
        {
            "users": users,
            "recent_readings": recent_readings,
            "recent_reviews": recent_reviews,
            "recent_comments": recent_comments,
        },
    )


PROTECTED_USER_IDS = {1}  # mc-admin


def _action(request, user_id, action):
    User = get_user_model()
    target = get_object_or_404(User, pk=user_id)
    if target.pk == request.user.pk or target.pk in PROTECTED_USER_IDS:
        return redirect("moderation")
    if action == "suspend":
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
    elif action == "staff":
        target.is_staff = not target.is_staff
        target.save(update_fields=["is_staff"])
    elif action == "delete":
        target.delete()
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
