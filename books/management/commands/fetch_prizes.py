from django.core.management.base import BaseCommand

from books import openlibrary
from books.models import Book, PrizeWinner
from books.wikidata import fetch


def _enrich_book(title: str, author: str) -> dict:
    """Essaie d'obtenir olid + cover_id + description via Open Library."""
    out = {"olid": "", "cover_id": None, "description": ""}
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


def _get_book(book_qid: str, title: str, author: str) -> Book | None:
    """Crée/récupère un Book (enrichi OL si possible) pour favori/liste.

    Quand l'ouvrage n'est pas connu (titre vide), on crée un Book sur le
    nom du lauréat pour garder coeur + liste disponibles côté interface.
    """
    if not title and not author:
        return None
    search_title = title or author
    enr = _enrich_book(search_title, author if title else "")
    if enr["olid"]:
        olid = enr["olid"]
    elif book_qid and not book_qid.startswith("nowork:"):
        olid = f"wd:{book_qid}"
    else:
        olid = f"wdn:{abs(hash((title, author))) % 10**10}"
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


def persist(rows, stdout=None) -> tuple[int, int]:
    kept, created = 0, 0
    for r in rows:
        book = _get_book(r["book_qid"], r["title"], r["author"])
        _, was_new = PrizeWinner.objects.update_or_create(
            prize_qid=r["prize_qid"], book_qid=r["book_qid"],
            defaults={
                "prize_name": r["prize_name"],
                "title": r["title"][:500],
                "author": r["author"][:300],
                "year": r["year"],
                "book": book,
            },
        )
        kept += 1
        if was_new:
            created += 1
    if stdout:
        stdout.write(f"persisted: {kept} lauréats ({created} nouveaux)")
    return kept, created


class Command(BaseCommand):
    help = "Récupère les lauréats via Wikidata (4 dernières années) + enrichit depuis Open Library."

    def handle(self, *a, **o):
        try:
            rows = fetch()
        except Exception as e:
            self.stderr.write(f"wikidata: {e}")
            return
        persist(rows, self.stdout)
