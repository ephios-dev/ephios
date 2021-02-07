# Generated by Django 3.1.6 on 2021-02-07 12:21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import ephios.extra.json


class Migration(migrations.Migration):

    replaces = [
        ("event_management", "0001_squashed_0009_auto_20200921_2155"),
        ("event_management", "0002_auto_20200927_2157"),
        ("event_management", "0003_auto_20201022_1620"),
        ("event_management", "0004_abstractparticipation_data"),
        ("event_management", "0005_eventtypepreference"),
        ("event_management", "0006_auto_20210204_2257"),
        ("event_management", "0007_auto_20210207_1309"),
    ]

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contenttypes", "0002_remove_content_type_name"),
        ("user_management", "0001_squashed_0008_auto_20210207_1309"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventType",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("title", models.CharField(max_length=254, verbose_name="title")),
                (
                    "can_grant_qualification",
                    models.BooleanField(verbose_name="can grant qualification"),
                ),
            ],
            options={
                "verbose_name": "event type",
                "verbose_name_plural": "event types",
            },
        ),
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("title", models.CharField(max_length=254, verbose_name="title")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="description"),
                ),
                ("location", models.CharField(max_length=254, verbose_name="location")),
                (
                    "type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="eventtype",
                        verbose_name="event type",
                    ),
                ),
                ("active", models.BooleanField(default=False)),
                (
                    "mail_updates",
                    models.BooleanField(default=True, verbose_name="send updates via mail"),
                ),
            ],
            options={
                "verbose_name": "event",
                "verbose_name_plural": "events",
                "permissions": [("view_past_event", "Can view past events")],
            },
        ),
        migrations.CreateModel(
            name="Shift",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("meeting_time", models.DateTimeField(verbose_name="meeting time")),
                ("start_time", models.DateTimeField(verbose_name="start time")),
                ("end_time", models.DateTimeField(verbose_name="end time")),
                ("signup_method_slug", models.SlugField(verbose_name="signup method")),
                (
                    "signup_configuration",
                    models.JSONField(
                        decoder=ephios.extra.json.CustomJSONDecoder,
                        default=dict,
                        encoder=ephios.extra.json.CustomJSONEncoder,
                    ),
                ),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shifts",
                        to="event",
                        verbose_name="shifts",
                    ),
                ),
            ],
            options={
                "verbose_name": "shift",
                "verbose_name_plural": "shifts",
            },
        ),
        migrations.CreateModel(
            name="AbstractParticipation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "state",
                    models.IntegerField(
                        choices=[
                            (0, "requested"),
                            (1, "confirmed"),
                            (2, "declined by user"),
                            (3, "rejected by responsible"),
                        ],
                        default=0,
                        verbose_name="state",
                    ),
                ),
                (
                    "shift",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="shift",
                        verbose_name="shift",
                    ),
                ),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_event_management.abstractparticipation_set+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "base_manager_name": "objects",
            },
        ),
        migrations.CreateModel(
            name="LocalParticipation",
            fields=[
                (
                    "abstractparticipation_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="abstractparticipation",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "base_manager_name": "objects",
            },
            bases=("user_management.abstractparticipation",),
        ),
        migrations.AlterModelOptions(
            name="shift",
            options={
                "ordering": ("meeting_time", "start_time", "id"),
                "verbose_name": "shift",
                "verbose_name_plural": "shifts",
            },
        ),
        migrations.AddField(
            model_name="abstractparticipation",
            name="data",
            field=models.JSONField(default=dict),
        ),
        migrations.CreateModel(
            name="EventTypePreference",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "section",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default=None,
                        max_length=150,
                        null=True,
                        verbose_name="Section Name",
                    ),
                ),
                ("name", models.CharField(db_index=True, max_length=150, verbose_name="Name")),
                ("raw_value", models.TextField(blank=True, null=True, verbose_name="Raw Value")),
                (
                    "instance",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="eventtype"),
                ),
            ],
        ),
        migrations.AlterField(
            model_name="abstractparticipation",
            name="state",
            field=models.IntegerField(
                choices=[
                    (0, "requested"),
                    (1, "confirmed"),
                    (2, "declined by user"),
                    (3, "rejected by responsible"),
                    (4, "getting dispatched"),
                ],
                verbose_name="state",
            ),
        ),
        migrations.AlterModelOptions(
            name="abstractparticipation",
            options={},
        ),
        migrations.AlterModelOptions(
            name="localparticipation",
            options={},
        ),
        migrations.AlterModelTable(
            name="abstractparticipation",
            table="abstractparticipation",
        ),
        migrations.AlterModelTable(
            name="event",
            table="event",
        ),
        migrations.AlterModelTable(
            name="eventtype",
            table="eventtype",
        ),
        migrations.AlterModelTable(
            name="eventtypepreference",
            table="eventtypepreference",
        ),
        migrations.AlterModelTable(
            name="localparticipation",
            table="localparticipation",
        ),
        migrations.AlterModelTable(
            name="shift",
            table="shift",
        ),
    ]
