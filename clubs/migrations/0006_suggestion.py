from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0005_readinglist_kind"),
        ("books", "0007_prizewinner_canonicalize_books"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Suggestion",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.CharField(blank=True, max_length=280, verbose_name="message")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("book", models.ForeignKey(on_delete=models.deletion.CASCADE, to="books.book")),
                ("recipient", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="suggestions_received", to=settings.AUTH_USER_MODEL)),
                ("sender", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="suggestions_sent", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="suggestion",
            constraint=models.CheckConstraint(
                condition=models.Q(("sender", models.F("recipient")), _negated=True),
                name="suggestion_no_self",
            ),
        ),
    ]
