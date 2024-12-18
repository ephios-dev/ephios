# Generated by Django 3.1.7 on 2021-03-24 20:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_eventtype_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="abstractparticipation",
            name="finished",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="abstractparticipation",
            name="data",
            field=models.JSONField(default=dict, verbose_name="Signup data"),
        ),
    ]
