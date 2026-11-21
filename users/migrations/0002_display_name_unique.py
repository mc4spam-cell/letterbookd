from django.db import migrations, models


def backfill_display_names(apps, schema_editor):
    User = apps.get_model("users", "User")
    taken = set(
        User.objects.exclude(display_name="")
        .values_list("display_name", flat=True)
    )
    for u in User.objects.filter(display_name="").order_by("pk"):
        base = (u.email or "").split("@")[0].strip()[:72] or f"membre{u.pk}"
        name, i = base, 2
        while name.lower() in {t.lower() for t in taken}:
            name = f"{base}{i}"
            i += 1
        u.display_name = name[:80]
        u.save(update_fields=["display_name"])
        taken.add(u.display_name)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_display_names, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="display_name",
            field=models.CharField(max_length=80, unique=True, verbose_name="nom affiché"),
        ),
    ]
