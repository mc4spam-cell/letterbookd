from django.core.management.base import BaseCommand

from books.importer import get_or_create_book
from books.models import Book, PrizeWinner
from books.text import norm_name
from books.wikipedia import fetch as fetch_wikipedia


def persist(rows, stdout=None) -> tuple[int, int]:
    # Évite de retaper Open Library à chaque exécution : cache par (titre, auteur) normalisés.
    cache: dict[tuple[str, str], Book] = {}
    for p in PrizeWinner.objects.filter(book__isnull=False).select_related("book"):
        cache[(norm_name(p.title), norm_name(p.author))] = p.book
    kept, created = 0, 0
    for r in rows:
        key = (norm_name(r["title"]), norm_name(r["author"]))
        book = cache.get(key) or get_or_create_book(
            r["title"], r["author"], placeholder_prefix="wp"
        )
        if book:
            cache[key] = book
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
    help = (
        "Scrape Wikipédia FR pour les 12 prix littéraires (toutes années) "
        "et enrichit depuis Open Library."
    )

    def handle(self, **o):
        rows = fetch_wikipedia()
        self.stdout.write(f"wikipedia: {len(rows)} lignes récupérées")
        persist(rows, self.stdout)
