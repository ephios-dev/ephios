# Generated by Django 3.1.7 on 2021-03-27 14:36

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import ephios.modellogging.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LogEntry",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("content_object_id", models.PositiveIntegerField(db_index=True)),
                ("attached_to_object_id", models.PositiveIntegerField(db_index=True)),
                ("datetime", models.DateTimeField(auto_now_add=True)),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            (
                                ephios.modellogging.models.InstanceActionType["CREATE"],
                                ephios.modellogging.models.InstanceActionType["CREATE"],
                            ),
                            (
                                ephios.modellogging.models.InstanceActionType["CHANGE"],
                                ephios.modellogging.models.InstanceActionType["CHANGE"],
                            ),
                            (
                                ephios.modellogging.models.InstanceActionType["DELETE"],
                                ephios.modellogging.models.InstanceActionType["DELETE"],
                            ),
                        ],
                        max_length=255,
                    ),
                ),
                ("request_id", models.CharField(blank=True, max_length=36, null=True)),
                (
                    "data",
                    models.JSONField(
                        default=dict, encoder=ephios.modellogging.models.LogJSONEncoder
                    ),
                ),
                (
                    "attached_to_object_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="logs_for_me",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="logs_about_me",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="logging_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-datetime", "-id"),
            },
        ),
    ]
