from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Follow, Invitation, Reading
from .visibility import followed_ids


@login_required
def home(request):
    """Accueil : les lectures récentes des membres que je suis."""
    ids = followed_ids(request.user)
    readings = (
        Reading.objects.filter(user_id__in=ids)
        .select_related("user", "book")
        .order_by("-created_at")[:60]
    )
    return render(request, "clubs/home.html", {"readings": readings})


@login_required
def members(request):
    User = get_user_model()
    me = request.user
    following = set(followed_ids(me))
    people = User.objects.exclude(pk=me.pk).order_by("display_name", "email")
    return render(
        request, "clubs/members.html", {"people": people, "following": following}
    )


@login_required
def follow(request, user_id):
    if request.method == "POST" and request.user.pk != user_id:
        target = get_object_or_404(get_user_model(), pk=user_id)
        Follow.objects.get_or_create(follower=request.user, followed=target)
    return redirect(request.META.get("HTTP_REFERER") or "home")


@login_required
def unfollow(request, user_id):
    if request.method == "POST":
        Follow.objects.filter(follower=request.user, followed_id=user_id).delete()
    return redirect(request.META.get("HTTP_REFERER") or "home")


@login_required
def profile_detail(request, user_id):
    other = get_object_or_404(get_user_model(), pk=user_id)
    following = Follow.objects.filter(follower=request.user, followed=other).exists()
    from django.db.models import F

    readings = (
        Reading.objects.filter(user=other)
        .select_related("book")
        .order_by(F("rating").desc(nulls_last=True), "-updated_at")
    )
    return render(
        request,
        "clubs/profile.html",
        {
            "profile_user": other,
            "following": following,
            "is_self": other.pk == request.user.pk,
            "readings": readings,
        },
    )


def accept_invitation(request, token):
    inv = Invitation.objects.filter(token=token, used_at__isnull=True).first()
    if inv is None:
        return render(request, "clubs/invite_invalid.html", status=404)
    request.session["invitation_token"] = token
    return redirect("account_signup")


@login_required
def invites(request):
    if request.method == "POST":
        Invitation.objects.create(created_by=request.user)
        return redirect("invites")
    my_invites = Invitation.objects.filter(created_by=request.user)
    return render(request, "clubs/invites.html", {"invites": my_invites})


@login_required
def me_settings(request):
    user = request.user
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            user.delete()
            return redirect("home")
        user.display_name = (request.POST.get("display_name") or "").strip()[:80]
        user.bio = (request.POST.get("bio") or "").strip()
        user.save(update_fields=["display_name", "bio"])
        return redirect("me_settings")
    return render(request, "clubs/me.html", {})
