from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0004_invitation_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="readinglist",
            name="kind",
            field=models.CharField(
                choices=[
                    ("normal", "normale"),
                    ("favorites", "favoris"),
                    ("toread", "à lire"),
                ],
                default="normal",
                max_length=16,
            ),
        ),
    ]
