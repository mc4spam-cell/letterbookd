from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("books", "0003_newrelease_prizewinner")]

    operations = [
        migrations.AlterField(
            model_name="newrelease",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="prizewinner",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
    ]
