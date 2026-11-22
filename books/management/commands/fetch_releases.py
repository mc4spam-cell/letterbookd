from django.core.management.base import BaseCommand

from books import openlibrary
from books.lemonde import fetch
from books.models import Book, NewRelease

SOURCE = "lemonde"


def _enrich(title: str, author: str) -> dict:
    out = {"olid": "", "cover_id": None, "description": ""}
    m = openlibrary.best_match(title, author)
    if not m:
        return out
    out["olid"] = m.get("olid") or ""
    out["cover_id"] = m.get("cover_id")
    if out["olid"]:
        w = openlibrary.fetch_work(out["olid"])
        if w:
            out["description"] = w.get("description") or ""
            if not out["cover_id"] and w.get("cover_id"):
                out["cover_id"] = w["cover_id"]
    return out


def _get_book(title: str, author: str) -> Book:
    enr = _enrich(title, author)
    if enr["olid"]:
        olid = enr["olid"]
    else:
        olid = f"lm:{abs(hash((title, author))) % 10**10}"
    defaults = {"title": title[:500], "authors": author[:500]}
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


class Command(BaseCommand):
    help = "Récupère les nouveautés du RSS Le Monde + enrichit via Open Library."

    def handle(self, *a, **o):
        try:
            items = fetch()
        except Exception as e:
            self.stderr.write(f"{SOURCE}: {e}")
            return
        kept, created = 0, 0
        for it in items:
            book = _get_book(it["title"], it["author"])
            _, was_new = NewRelease.objects.update_or_create(
                source=SOURCE, title=it["title"][:500], author=it["author"][:300],
                defaults={
                    "cover_url": it["cover_url"][:500],
                    "summary": it["summary"],
                    "source_url": it["source_url"][:500],
                    "book": book,
                },
            )
            kept += 1
            if was_new:
                created += 1
        self.stdout.write(f"{SOURCE}: {kept} items ({created} nouveaux)")
