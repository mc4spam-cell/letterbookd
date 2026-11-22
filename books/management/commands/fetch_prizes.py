from django.core.management.base import BaseCommand

from books.models import Book, PrizeWinner
from books.wikidata import fetch


def _get_book(book_qid: str, title: str, author: str) -> Book | None:
    """Crée/récupère un Book pour permettre l'ajout aux favoris/listes."""
    if not title:
        return None
    olid = f"wd:{book_qid}" if book_qid and not book_qid.startswith("nowork:") else f"wdn:{abs(hash((title, author))) % 10**10}"
    book, _ = Book.objects.get_or_create(
        olid=olid, defaults={"title": title[:500], "authors": author[:500]},
    )
    return book


class Command(BaseCommand):
    help = "Récupère les lauréats de prix littéraires (Wikidata, 4 dernières années)."

    def handle(self, *a, **o):
        try:
            rows = fetch()
        except Exception as e:
            self.stderr.write(f"wikidata: {e}")
            return
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
        self.stdout.write(f"wikidata: {kept} lauréats ({created} nouveaux)")
