from django.core.management.base import BaseCommand

from books.importer import get_or_create_book
from books.lemonde import fetch
from books.models import NewRelease

SOURCE = "lemonde"


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
            book = get_or_create_book(it["title"], it["author"], placeholder_prefix="lm")
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
