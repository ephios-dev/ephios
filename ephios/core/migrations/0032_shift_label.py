# Generated by Django 5.0.9 on 2024-11-25 20:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0031_qualificationgrant_externally_managed_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="shift",
            name="label",
            field=models.CharField(
                blank=True,
                help_text="Optional label to help differentiate multiple shifts in an event.",
                max_length=255,
                verbose_name="Label",
            ),
        ),
    ]
