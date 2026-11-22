from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("books", "0004_alter_newrelease_id_alter_prizewinner_id")]

    operations = [
        migrations.AddField(
            model_name="newrelease",
            name="book",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=models.SET_NULL, to="books.book"
            ),
        ),
        migrations.AddField(
            model_name="prizewinner",
            name="book",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=models.SET_NULL, to="books.book"
            ),
        ),
    ]
