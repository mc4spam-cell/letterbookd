from django.core.management.base import BaseCommand

from books.models import PrizeWinner
from books.wikidata import fetch


class Command(BaseCommand):
    help = "Récupère les lauréats de prix littéraires (Wikidata, depuis 2020)."

    def handle(self, *a, **o):
        try:
            rows = fetch()
        except Exception as e:
            self.stderr.write(f"wikidata: {e}")
            return
        kept, created = 0, 0
        for r in rows:
            if not r["book_qid"] or not r["title"]:
                continue
            _, was_new = PrizeWinner.objects.update_or_create(
                prize_qid=r["prize_qid"], book_qid=r["book_qid"],
                defaults={
                    "prize_name": r["prize_name"],
                    "title": r["title"][:500],
                    "author": r["author"][:300],
                    "year": r["year"],
                },
            )
            kept += 1
            if was_new:
                created += 1
        self.stdout.write(f"wikidata: {kept} lauréats ({created} nouveaux)")
