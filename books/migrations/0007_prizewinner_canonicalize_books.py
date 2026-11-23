from django.db import migrations

from books.text import norm_name


def _author_matches(a: str, b: str) -> bool:
    return not a or not b or a == b or a in b or b in a


def canonicalize(apps, schema_editor):
    PrizeWinner = apps.get_model("books", "PrizeWinner")
    Book = apps.get_model("books", "Book")
    PrizeWinner.objects.filter(prize_qid__regex=r"^Q\d").delete()
    books_by_key: dict[tuple[str, str], object] = {}
    for b in Book.objects.order_by("pk").only("pk", "title", "authors"):
        books_by_key.setdefault((norm_name(b.title), norm_name(b.authors)), b)
    for pw in PrizeWinner.objects.only("pk", "title", "author", "book_id"):
        nt = norm_name(pw.title)
        na = norm_name(pw.author)
        hit = books_by_key.get((nt, na)) or next(
            (b for (k_nt, k_na), b in books_by_key.items()
             if k_nt == nt and _author_matches(na, k_na)),
            None,
        )
        if hit and pw.book_id != hit.pk:
            PrizeWinner.objects.filter(pk=pw.pk).update(book_id=hit.pk)


class Migration(migrations.Migration):
    dependencies = [("books", "0006_prizewinner_book_qid_length")]
    operations = [migrations.RunPython(canonicalize, migrations.RunPython.noop)]
