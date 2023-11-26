# Generated by Django 4.2.6 on 2023-11-26 16:30

from django.db import migrations, models

import ephios.extra.json


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0024_identityprovider_create_missing_groups_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="notification",
            name="failed",
        ),
        migrations.AddField(
            model_name="notification",
            name="processed_by",
            field=models.JSONField(
                blank=True,
                decoder=ephios.extra.json.CustomJSONDecoder,
                default=list,
                encoder=ephios.extra.json.CustomJSONEncoder,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="read",
            field=models.BooleanField(default=False, verbose_name="read"),
        ),
    ]
