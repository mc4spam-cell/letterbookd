from django.core.management.base import BaseCommand

from books.lemonde import fetch
from books.models import Book, NewRelease

SOURCE = "lemonde"


def _get_book(title: str, author: str, cover_url: str) -> Book:
    olid = f"lm:{abs(hash((title, author))) % 10**10}"
    book, _ = Book.objects.get_or_create(
        olid=olid, defaults={"title": title[:500], "authors": author[:500]},
    )
    if cover_url and not book.description:
        book.description = ""
    return book


class Command(BaseCommand):
    help = "Récupère les nouveautés livres via le RSS du Monde et met à jour NewRelease."

    def handle(self, *a, **o):
        try:
            items = fetch()
        except Exception as e:
            self.stderr.write(f"{SOURCE}: {e}")
            return
        kept, created = 0, 0
        for it in items:
            book = _get_book(it["title"], it["author"], it["cover_url"])
            obj, was_new = NewRelease.objects.update_or_create(
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
