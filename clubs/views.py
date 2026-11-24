from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .list_views import _suggest_recipients
from .models import Follow, Invitation, Reading
from .safe_redirect import safe_back
from .visibility import followed_ids


@login_required
def home(request):
    """Accueil : lectures récentes, suivis d'abord, puis les autres."""
    ids = followed_ids(request.user)
    followed_readings = (
        Reading.objects.filter(user_id__in=ids)
        .select_related("user", "book")
        .order_by("-created_at")[:10]
    )
    others_readings = (
        Reading.objects.exclude(user_id__in=ids)
        .exclude(user=request.user)
        .exclude(user__is_deleted=True)
        .select_related("user", "book")
        .order_by("-created_at")[:2]
    )
    return render(
        request,
        "clubs/home.html",
        {
            "followed_readings": followed_readings,
            "others_readings": others_readings,
            "suggest_recipients": _suggest_recipients(request),
        },
    )


@login_required
def members(request):
    User = get_user_model()
    me = request.user
    following = set(followed_ids(me))
    people = (
        User.objects.filter(pk__in=following)
        .order_by("display_name", "email")
    )
    return render(
        request, "clubs/members.html", {"people": people, "following": following}
    )


@login_required
def follow(request, user_id):
    if request.method == "POST" and request.user.pk != user_id:
        target = get_object_or_404(get_user_model(), pk=user_id, is_deleted=False)
        Follow.objects.get_or_create(follower=request.user, followed=target)
    return redirect(safe_back(request, "home"))


@login_required
def unfollow(request, user_id):
    if request.method == "POST":
        Follow.objects.filter(follower=request.user, followed_id=user_id).delete()
    return redirect(safe_back(request, "home"))


@login_required
def profile_detail(request, user_id):
    other = get_object_or_404(get_user_model(), pk=user_id, is_deleted=False)
    following = Follow.objects.filter(follower=request.user, followed=other).exists()
    from django.db.models import F

    from .models import ReadingList
    readings = (
        Reading.objects.filter(user=other)
        .select_related("book")
        .order_by(F("rating").desc(nulls_last=True), "-updated_at")
    )
    lists = (
        ReadingList.objects.filter(owner=other)
        .order_by("-updated_at")
        .prefetch_related("items__book")
    )
    return render(
        request,
        "clubs/profile.html",
        {
            "profile_user": other,
            "following": following,
            "is_self": other.pk == request.user.pk,
            "readings": readings,
            "lists": lists,
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
        Invitation.objects.filter(created_by=request.user, used_at__isnull=True).delete()
        Invitation.objects.create(created_by=request.user)
        return redirect("invites")
    my_invites = Invitation.objects.filter(created_by=request.user)
    return render(request, "clubs/invites.html", {"invites": my_invites})


@login_required
def me_settings(request):
    user = request.user
    error = None
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            user.delete()
            return redirect("home")
        new_name = (request.POST.get("display_name") or "").strip()[:80]
        if not new_name:
            error = "Le nom de membre est obligatoire."
        elif (
            get_user_model().objects.filter(display_name__iexact=new_name)
            .exclude(pk=user.pk)
            .exists()
        ):
            error = "Ce nom est déjà pris, choisis-en un autre."
        else:
            user.display_name = new_name
            user.bio = (request.POST.get("bio") or "").strip()
            user.save(update_fields=["display_name", "bio"])
            return redirect("me_settings")
    return render(request, "clubs/me.html", {"error": error})
