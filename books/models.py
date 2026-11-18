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
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def cover_url(self, size: str = "M") -> str:
        return (
            f"https://covers.openlibrary.org/b/id/{self.cover_id}-{size}.jpg"
            if self.cover_id
            else ""
        )
