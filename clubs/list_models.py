from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ReadingList(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lists"
    )
    name = models.CharField(_("titre"), max_length=120)
    description = models.TextField(_("description"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class ListItem(models.Model):
    list = models.ForeignKey(ReadingList, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)
    note = models.TextField(_("note libre"), blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["list", "book"], name="uniq_list_book"),
        ]
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.book} dans {self.list}"
