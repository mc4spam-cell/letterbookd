"""Client minimal Open Library : seulement la recherche.

L'ajout d'un livre réutilise les champs renvoyés par la recherche : pas de
second appel, un seul aller-retour par livre importé.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEARCH_URL = "https://openlibrary.org/search.json"
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
    out = []
    for d in data.get("docs", []):
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
