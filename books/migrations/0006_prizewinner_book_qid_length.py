from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("books", "0005_newrelease_book_prizewinner_book")]

    operations = [
        migrations.AlterField(
            model_name="prizewinner",
            name="book_qid",
            field=models.CharField(max_length=128),
        ),
    ]
