# Generated by Django 3.0.9 on 2020-09-01 22:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("event_management", "0006_auto_20200830_0116"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="event",
            options={
                "permissions": [("view_past_event", "Can view events in the past")],
                "verbose_name": "event",
                "verbose_name_plural": "events",
            },
        ),
    ]
