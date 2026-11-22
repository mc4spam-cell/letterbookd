"""Client minimal Open Library : seulement la recherche.

L'ajout d'un livre réutilise les champs renvoyés par la recherche : pas de
second appel, un seul aller-retour par livre importé.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEARCH_URL = "https://openlibrary.org/search.json"
WORK_URL = "https://openlibrary.org/works/{olid}.json"
USER_AGENT = "letterbookd/0.1 (private book club tool)"


def search(query: str, limit: int = 10) -> list[dict]:
    """Interroge Open Library et renvoie une liste normalisée.

    Jamais appelée en test : `urlopen` est patché par la fixture.
    """
    q = (query or "").strip()
    if not q:
        return []
    url = f"{SEARCH_URL}?{urlencode({'q': q, 'limit': limit})}"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return _normalize_docs(data.get("docs", []))


def _normalize_docs(docs):
    out = []
    for d in docs:
        key = (d.get("key") or "").removeprefix("/works/")
        if not key:
            continue
        out.append(
            {
                "olid": key,
                "title": d.get("title") or "",
                "authors": ", ".join(d.get("author_name") or []),
                "isbn": (d.get("isbn") or [""])[0],
                "pages": d.get("number_of_pages_median"),
                "cover_id": d.get("cover_i"),
                "year": d.get("first_publish_year"),
            }
        )
    return out


def best_match(title: str, author: str = "") -> dict | None:
    """Recherche OL best-effort : premier résultat qui correspond au titre.

    Renvoie un dict normalisé (olid/cover_id/…) ou None. Erreurs avalées.
    """
    if not title:
        return None
    try:
        results = search(f"{title} {author}".strip(), limit=5)
    except Exception:
        return None
    if not results:
        return None
    return results[0]


def fetch_work(olid: str) -> dict:
    """Détail d'une œuvre : description + covers. Vide si indisponible."""
    olid = (olid or "").strip()
    if not olid:
        return {}
    url = WORK_URL.format(olid=olid)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}
    desc = data.get("description") or ""
    if isinstance(desc, dict):
        desc = desc.get("value") or ""
    covers = data.get("covers") or []
    return {"description": desc, "cover_id": covers[0] if covers else None}
