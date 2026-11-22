from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0002_display_name_unique")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="last_ip",
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name="dernière IP"),
        ),
        migrations.AddField(
            model_name="user",
            name="is_deleted",
            field=models.BooleanField(default=False, verbose_name="supprimé"),
        ),
    ]
