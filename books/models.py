from django.db import models
from django.utils.translation import gettext_lazy as _


class Book(models.Model):
    olid = models.CharField(_("identifiant Open Library"), max_length=40, unique=True)
    title = models.CharField(_("titre"), max_length=500)
    authors = models.CharField(_("auteurs"), max_length=500, blank=True)
    isbn = models.CharField(_("ISBN"), max_length=20, blank=True)
    pages = models.PositiveIntegerField(_("pages"), null=True, blank=True)
    cover_id = models.PositiveIntegerField(null=True, blank=True)
    year = models.PositiveIntegerField(_("année"), null=True, blank=True)
    description = models.TextField(_("résumé"), blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def _cover(self, size: str) -> str:
        return (
            f"https://covers.openlibrary.org/b/id/{self.cover_id}-{size}.jpg"
            if self.cover_id
            else ""
        )

    @property
    def cover_url(self) -> str:
        return self._cover("M")

    @property
    def small_cover(self) -> str:
        return self._cover("S")

    @property
    def large_cover(self) -> str:
        return self._cover("L")

    def hydrate_from_openlibrary(self) -> None:
        """Enrichit description et cover_id manquants via /works/{olid}.json.

        Best-effort : les erreurs sont avalées pour ne jamais casser la vue.
        """
        from . import openlibrary

        data = openlibrary.fetch_work(self.olid)
        changed = False
        desc = data.get("description") or ""
        if desc and not self.description:
            self.description = desc[:4000]
            changed = True
        cov = data.get("cover_id")
        if cov and not self.cover_id:
            self.cover_id = cov
            changed = True
        if changed:
            self.save(update_fields=["description", "cover_id"])
