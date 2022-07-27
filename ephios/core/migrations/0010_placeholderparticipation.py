# Generated by Django 3.2.5 on 2021-07-03 13:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_auto_20210528_2230"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlaceholderParticipation",
            fields=[
                (
                    "abstractparticipation_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="core.abstractparticipation",
                    ),
                ),
                ("first_name", models.CharField(max_length=254)),
                ("last_name", models.CharField(max_length=254)),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("core.abstractparticipation",),
        ),
    ]
