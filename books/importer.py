"""Création/récupération d'un Book partagée entre les scrapers (prix, nouveautés).

Un seul endroit à corriger quand la stratégie d'olid évolue.
"""
from __future__ import annotations

import hashlib

from . import openlibrary
from .models import Book
from .text import norm_name


def _enrich(title: str, author: str) -> dict:
    out: dict = {"olid": "", "cover_id": None, "description": ""}
    m = openlibrary.best_match(title, author)
    if not m:
        return out
    out["olid"] = m.get("olid") or ""
    out["cover_id"] = m.get("cover_id")
    if out["olid"]:
        work = openlibrary.fetch_work(out["olid"])
        if work:
            out["description"] = work.get("description") or ""
            if not out["cover_id"] and work.get("cover_id"):
                out["cover_id"] = work["cover_id"]
    return out


def _author_matches(a: str, b: str) -> bool:
    return not a or not b or a == b or a in b or b in a


def _resolve_canonical(title: str, author: str) -> Book | None:
    """Book existant pour ce titre/auteur normalisé (plus petit pk), si présent."""
    nt = norm_name(title)
    if not nt:
        return None
    na = norm_name(author)
    for b in Book.objects.filter(title__iexact=title).order_by("pk"):
        if norm_name(b.title) == nt and _author_matches(na, norm_name(b.authors)):
            return b
    return None


def _stable_placeholder(prefix: str, title: str, author: str) -> str:
    """olid déterministe quand OL ne trouve rien (pas de hash() aléatoire)."""
    key = f"{title}|{author}".encode("utf-8")
    return f"{prefix}:{hashlib.md5(key).hexdigest()[:16]}"


def get_or_create_book(
    title: str, author: str, *, placeholder_prefix: str = "lb"
) -> Book | None:
    """Renvoie le Book canonique pour (title, author), en enrichissant via OL."""
    if not title and not author:
        return None
    canonical = _resolve_canonical(title or author, author if title else "")
    if canonical:
        return canonical
    enr = _enrich(title or author, author if title else "")
    olid = enr["olid"] or _stable_placeholder(placeholder_prefix, title, author)
    defaults = {"title": (title or author)[:500], "authors": author[:500]}
    if enr["cover_id"]:
        defaults["cover_id"] = enr["cover_id"]
    if enr["description"]:
        defaults["description"] = enr["description"][:4000]
    book, created = Book.objects.get_or_create(olid=olid, defaults=defaults)
    if not created:
        changed = False
        if enr["cover_id"] and not book.cover_id:
            book.cover_id = enr["cover_id"]
            changed = True
        if enr["description"] and not book.description:
            book.description = enr["description"][:4000]
            changed = True
        if changed:
            book.save(update_fields=["cover_id", "description"])
    return book
