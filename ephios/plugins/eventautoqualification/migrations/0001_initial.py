# Generated by Django 3.1.7 on 2021-03-22 18:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0006_notification"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventAutoQualificationConfiguration",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "expiration_date",
                    models.DateField(blank=True, null=True, verbose_name="Expiration date"),
                ),
                (
                    "mode",
                    models.IntegerField(
                        choices=[(1, "any shift"), (2, "every shift"), (3, "last shift")],
                        default=1,
                        verbose_name="Which shifts must be attended to acquire the qualification?",
                    ),
                ),
                (
                    "extend_only",
                    models.BooleanField(
                        default=False,
                        verbose_name="Only extend or reactivate existing qualification",
                    ),
                ),
                (
                    "needs_confirmation",
                    models.BooleanField(
                        default=True, verbose_name="Qualification must be confirmed afterwards"
                    ),
                ),
                (
                    "event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="auto_qualification_config",
                        to="core.event",
                    ),
                ),
                ("handled_for", models.ManyToManyField(to="core.AbstractParticipation")),
                (
                    "qualification",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="core.qualification"
                    ),
                ),
            ],
        ),
    ]
