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

        Best-effort : les erreurs sont avalées pour ne jamais casser la vue,
        et les olid synthétiques (lm:, wd:, wdn:) sont ignorés.
        """
        if not self.olid or ":" in self.olid:
            return
        from . import openlibrary
        try:
            data = openlibrary.fetch_work(self.olid)
        except Exception:
            return
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


class NewRelease(models.Model):
    """Nouveautés aspirées sur une source externe (Fnac pour l'instant)."""
    source = models.CharField(max_length=20, default="fnac")
    source_url = models.URLField(max_length=500, blank=True)
    title = models.CharField(_("titre"), max_length=500)
    author = models.CharField(_("auteur"), max_length=300, blank=True)
    cover_url = models.URLField(max_length=500, blank=True)
    summary = models.TextField(_("résumé"), blank=True)
    book = models.ForeignKey("Book", on_delete=models.SET_NULL, null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fetched_at", "title"]
        constraints = [
            models.UniqueConstraint(fields=["source", "title", "author"], name="uniq_release"),
        ]

    def __str__(self):
        return f"{self.title} — {self.author}"


class PrizeWinner(models.Model):
    """Lauréats de prix littéraires récupérés via Wikidata."""
    prize_qid = models.CharField(max_length=16)
    prize_name = models.CharField(max_length=120)
    book_qid = models.CharField(max_length=128)
    title = models.CharField(_("titre"), max_length=500)
    author = models.CharField(_("auteur"), max_length=300, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    book = models.ForeignKey("Book", on_delete=models.SET_NULL, null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "prize_name", "title"]
        constraints = [
            models.UniqueConstraint(fields=["prize_qid", "book_qid"], name="uniq_prize_book"),
        ]

    def __str__(self):
        return f"{self.prize_name} {self.year}: {self.title}"
