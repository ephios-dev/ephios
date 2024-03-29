# Generated by Django 3.2.4 on 2021-06-14 11:56

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("modellogging", "0003_alter_logentry_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="logentry",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="logging_entries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
