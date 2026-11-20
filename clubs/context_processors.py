from datetime import datetime
from pathlib import Path

try:
    _TS = float(Path("/app/.build_date").read_text().strip())
    _BUILD_DATE = datetime.fromtimestamp(_TS)
except Exception:
    _BUILD_DATE = None


def build_date(request):
    return {"BUILD_DATE": _BUILD_DATE}
