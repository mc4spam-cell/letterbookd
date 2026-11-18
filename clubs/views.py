from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from .models import Club, Membership, Role
from .visibility import visible_clubs


def _sole_host_clubs(user):
    hosting = Membership.objects.filter(user=user, role=Role.HOST).values("club_id")
    other_host = Membership.objects.filter(
        club_id=OuterRef("pk"), role=Role.HOST
    ).exclude(user=user)
    return (
        Club.objects.filter(pk__in=hosting)
        .annotate(has_other=Exists(other_host))
        .filter(has_other=False)
    )


@login_required
def home(request):
    clubs = visible_clubs(request.user)
    return render(request, "clubs/home.html", {"clubs": clubs})


@login_required
def club_create(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        if not name:
            return render(
                request,
                "clubs/club_form.html",
                {"error": _("Donne un nom au club."), "name": name, "description": description},
            )
        club = Club.objects.create(name=name, description=description)
        Membership.objects.create(user=request.user, club=club, role=Role.HOST)
        return redirect("club_detail", club_id=club.pk)
    return render(request, "clubs/club_form.html", {})


def _membership(user, club):
    if not user.is_authenticated:
        return None
    return Membership.objects.filter(user=user, club=club).first()


@login_required
def club_detail(request, club_id):
    club = get_object_or_404(Club, pk=club_id)
    me = _membership(request.user, club)
    if me is None:
        raise Http404
    members = club.members.all()
    from .cycle_views import current_selection, past_selections
    open_vote = club.votes.filter(closed_at__isnull=True).first()
    return render(
        request,
        "clubs/club_detail.html",
        {
            "club": club,
            "me": me,
            "members": members,
            "is_host": me.role == Role.HOST,
            "open_vote": open_vote,
            "current": current_selection(club),
            "past_selections": past_selections(club),
            "propositions": club.propositions.select_related("book"),
        },
    )


@login_required
def club_settings(request, club_id):
    club = get_object_or_404(Club, pk=club_id)
    me = _membership(request.user, club)
    if me is None or me.role != Role.HOST:
        raise Http404
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "rotate":
            club.rotate_invite()
        elif action == "exclude":
            target_id = request.POST.get("user_id")
            if target_id and str(request.user.pk) != str(target_id):
                Membership.objects.filter(
                    club=club, user_id=target_id, role=Role.MEMBER
                ).delete()
        elif action == "promote":
            target_id = request.POST.get("user_id")
            if target_id:
                Membership.objects.filter(
                    club=club, user_id=target_id, role=Role.MEMBER
                ).update(role=Role.HOST)
        return redirect("club_settings", club_id=club.pk)
    return render(
        request,
        "clubs/club_settings.html",
        {"club": club, "members": club.members.exclude(pk=request.user.pk)},
    )


@login_required
def join_by_token(request, token):
    club = get_object_or_404(Club, invite_token=token)
    Membership.objects.get_or_create(
        user=request.user, club=club, defaults={"role": Role.MEMBER}
    )
    return redirect("club_detail", club_id=club.pk)


@login_required
def profile_detail(request, user_id):
    from django.contrib.auth import get_user_model

    from .visibility import shares_club_with

    other = get_object_or_404(get_user_model(), pk=user_id)
    if not shares_club_with(request.user, other):
        raise Http404
    shared = visible_clubs(request.user).filter(membership__user=other)
    return render(
        request, "clubs/profile.html", {"profile_user": other, "shared_clubs": shared}
    )


@login_required
def me_settings(request):
    user = request.user
    blocking = list(_sole_host_clubs(user).values_list("name", flat=True))
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            if blocking:
                return render(
                    request,
                    "clubs/me.html",
                    {
                        "error": _(
                            "Tu es le seul animateur de ces clubs ; promeus un autre "
                            "membre avant de supprimer ton compte."
                        ),
                        "blocking_clubs": blocking,
                    },
                )
            user.delete()
            return redirect("home")
        user.display_name = (request.POST.get("display_name") or "").strip()[:80]
        user.bio = (request.POST.get("bio") or "").strip()
        user.save(update_fields=["display_name", "bio"])
        return redirect("me_settings")
    return render(request, "clubs/me.html", {"blocking_clubs": blocking})
