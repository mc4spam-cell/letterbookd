from datetime import datetime
from pathlib import Path

from .review_models import Notification, Suggestion

try:
    _TS = float(Path("/app/.build_date").read_text().strip())
    _BUILD_DATE = datetime.fromtimestamp(_TS)
except Exception:
    _BUILD_DATE = None


def build_date(request):
    return {"BUILD_DATE": _BUILD_DATE}


def unread_notifs(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"has_unread_notifs": False}
    n = Notification.objects.filter(recipient=user, read_at__isnull=True).values("pk")
    s = Suggestion.objects.filter(recipient=user, read_at__isnull=True).values("pk")
    return {"has_unread_notifs": n.union(s).exists()}
