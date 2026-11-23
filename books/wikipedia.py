"""Scrape Wikipédia FR, prix par prix, pour les lauréats de prix littéraires.

Parse les wikitables (gestion des rowspan), dédup par (année, auteur, titre),
et retourne toutes les années disponibles. L'enrichissement Open Library est
fait côté persist.
"""
from __future__ import annotations

import hashlib
import html
import re
import urllib.request

PRIZES = [
    ("goncourt",    "Prix_Goncourt",                            "Prix Goncourt"),
    ("lyceens",     "Prix_Goncourt_des_lyc%C3%A9ens",           "Prix Goncourt des Lycéens"),
    ("renaudot",    "Prix_Renaudot",                            "Prix Renaudot"),
    ("femina",      "Prix_Femina",                              "Prix Femina"),
    ("medicis",     "Prix_M%C3%A9dicis",                        "Prix Médicis"),
    ("interallie",  "Prix_Interalli%C3%A9",                     "Prix Interallié"),
    ("decembre",    "Prix_D%C3%A9cembre",                       "Prix Décembre"),
    (
        "academie",
        "Grand_prix_du_roman_de_l%27Acad%C3%A9mie_fran%C3%A7aise",
        "Grand prix du roman de l'Académie française",
    ),
    ("livre_inter", "Prix_du_Livre_Inter",                      "Prix du Livre Inter"),
    ("libraires",   "Prix_des_libraires",                       "Prix des Libraires"),
    ("roman_fnac",  "Prix_du_roman_Fnac",                       "Prix du roman Fnac"),
    (
        "5continents",
        "Prix_des_cinq_continents_de_la_francophonie",
        "Prix des cinq continents de la francophonie",
    ),
]

TABLE_RE = re.compile(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', re.DOTALL)
TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL)
CELL_RE = re.compile(r'<(t[dh])\b([^>]*)>(.*?)</\1>', re.DOTALL)
ROWSPAN_RE = re.compile(r'rowspan="?(\d+)"?')
TAG_RE = re.compile(r"<[^>]+>")
FOOTNOTE_RE = re.compile(r"\[\d+\]|\[note \d+\]", re.IGNORECASE)
HIDDEN_RE = re.compile(r'<span[^>]*style="[^"]*display\s*:\s*none[^"]*"[^>]*>.*?</span>', re.DOTALL)
UA = "letterbookd/0.1 (private book club)"


def _clean(s: str) -> str:
    s = HIDDEN_RE.sub("", s)
    s = TAG_RE.sub("", s)
    s = html.unescape(s)
    s = FOOTNOTE_RE.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def _fetch_page(slug: str) -> str:
    req = urllib.request.Request(
        f"https://fr.wikipedia.org/wiki/{slug}", headers={"User-Agent": UA}
    )
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def _parse_table(html_table: str) -> list[list[str]]:
    """Parse un wikitable en grille, en respectant les rowspan."""
    rows_raw = TR_RE.findall(html_table)
    grid: list[list[str]] = []
    pending: dict[int, tuple[str, int]] = {}  # col -> (value, remaining rows)
    for raw in rows_raw:
        cells_raw = CELL_RE.findall(raw)
        if not cells_raw:
            continue
        row: list[str] = []
        c = 0
        it = iter(cells_raw)
        tac = next(it, None)
        while True:
            if c in pending:
                v, rem = pending[c]
                row.append(v)
                if rem - 1 <= 0:
                    del pending[c]
                else:
                    pending[c] = (v, rem - 1)
                c += 1
                continue
            if tac is None:
                break
            _, attrs, content = tac
            text = _clean(content)
            m = ROWSPAN_RE.search(attrs)
            rs = int(m.group(1)) if m else 1
            row.append(text)
            if rs > 1:
                pending[c] = (text, rs - 1)
            c += 1
            tac = next(it, None)
        grid.append(row)
    return grid


def _detect_columns(headers: list[str]) -> dict[str, int] | None:
    h_clean = [_clean(h).lower() for h in headers]
    cols: dict[str, int] = {}
    for i, h in enumerate(h_clean):
        if h.startswith("année"):
            cols["year"] = i
        elif h in ("auteur", "lauréat", "lauréate", "auteur[4]"):
            cols["author"] = i
        elif h in ("ouvrage", "titre", "ouvrage[4]"):
            cols["title"] = i
    if "year" in cols and "author" in cols and "title" in cols:
        return cols
    return None


def _extract(grid: list[list[str]]) -> list[tuple[int, str, str]]:
    if not grid:
        return []
    cols = _detect_columns(grid[0])
    if cols is None:
        return []
    out: list[tuple[int, str, str]] = []
    mx = max(cols.values())
    for row in grid[1:]:
        if len(row) <= mx:
            continue
        ym = re.search(r"\d{4}", row[cols["year"]])
        if not ym:
            continue
        out.append((int(ym.group()), row[cols["author"]], row[cols["title"]]))
    return out


def _book_qid(year: int, author: str, title: str) -> str:
    key = f"{year}|{author}|{title}".encode()
    return "wp:" + hashlib.md5(key).hexdigest()[:20]


def fetch() -> list[dict]:
    """Toutes les années pour les 12 prix, format compatible persist()."""
    rows: list[dict] = []
    for prize_qid, slug, prize_name in PRIZES:
        try:
            page = _fetch_page(slug)
        except Exception:
            continue
        seen: set[tuple[int, str, str]] = set()
        for t in TABLE_RE.findall(page):
            for year, author, title in _extract(_parse_table(t)):
                k = (year, author, title)
                if k in seen:
                    continue
                seen.add(k)
                if not author and not title:
                    continue
                rows.append({
                    "prize_qid": prize_qid,
                    "prize_name": prize_name,
                    "book_qid": _book_qid(year, author, title),
                    "title": title,
                    "author": author,
                    "year": year,
                })
    return rows
