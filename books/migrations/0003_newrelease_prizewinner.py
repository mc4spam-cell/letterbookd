from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("books", "0002_book_description")]

    operations = [
        migrations.CreateModel(
            name="NewRelease",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("source", models.CharField(default="fnac", max_length=20)),
                ("source_url", models.URLField(blank=True, max_length=500)),
                ("title", models.CharField(max_length=500, verbose_name="titre")),
                ("author", models.CharField(blank=True, max_length=300, verbose_name="auteur")),
                ("cover_url", models.URLField(blank=True, max_length=500)),
                ("summary", models.TextField(blank=True, verbose_name="résumé")),
                ("fetched_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-fetched_at", "title"]},
        ),
        migrations.AddConstraint(
            model_name="newrelease",
            constraint=models.UniqueConstraint(
                fields=("source", "title", "author"), name="uniq_release"
            ),
        ),
        migrations.CreateModel(
            name="PrizeWinner",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("prize_qid", models.CharField(max_length=16)),
                ("prize_name", models.CharField(max_length=120)),
                ("book_qid", models.CharField(max_length=16)),
                ("title", models.CharField(max_length=500, verbose_name="titre")),
                ("author", models.CharField(blank=True, max_length=300, verbose_name="auteur")),
                ("year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("fetched_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-year", "prize_name", "title"]},
        ),
        migrations.AddConstraint(
            model_name="prizewinner",
            constraint=models.UniqueConstraint(
                fields=("prize_qid", "book_qid"), name="uniq_prize_book"
            ),
        ),
    ]
