# Generated by Django 3.0.9 on 2020-09-06 19:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("event_management", "0007_auto_20200902_0016"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="mail_updates",
            field=models.BooleanField(default=True, verbose_name="send updates via mail"),
        ),
    ]
