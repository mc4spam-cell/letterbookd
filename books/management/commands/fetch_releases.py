from django.core.management.base import BaseCommand

from books.fnac import fetch
from books.models import NewRelease


class Command(BaseCommand):
    help = "Récupère les nouveautés livres sur fnac.com et met à jour NewRelease."

    def handle(self, *a, **o):
        try:
            items = fetch()
        except Exception as e:
            self.stderr.write(f"fnac: {e}")
            return
        kept, created = 0, 0
        for it in items:
            obj, was_new = NewRelease.objects.update_or_create(
                source="fnac", title=it["title"][:500], author=it["author"][:300],
                defaults={
                    "cover_url": it["cover_url"][:500],
                    "summary": it["summary"],
                    "source_url": it["source_url"][:500],
                },
            )
            kept += 1
            if was_new:
                created += 1
        self.stdout.write(f"fnac: {kept} items ({created} nouveaux)")
