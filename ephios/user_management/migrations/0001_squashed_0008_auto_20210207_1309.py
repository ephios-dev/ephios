# Generated by Django 3.1.6 on 2021-02-07 12:24

import datetime
import secrets
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import ephios.extra.json


def create_initial_permissions(apps, schema_editor):
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    group_content_type = ContentType.objects.get_for_model(Group)
    Permission.objects.create(
        name="Decide whether requested working hours should be granted",
        codename="decide_workinghours_for_group",
        content_type=group_content_type,
    )
    Permission.objects.create(
        name="Publish event for group",
        codename="publish_event_for_group",
        content_type=group_content_type,
    )


class Migration(migrations.Migration):
    replaces = [
        ("user_management", "0001_initial"),
        ("user_management", "0002_initial_permissions"),
        ("user_management", "0003_userprofile_calendar_token_squashed_0008_auto_20200925_1640"),
        ("user_management", "0004_auto_20201014_1648"),
        ("user_management", "0005_auto_20210106_2219"),
        ("user_management", "0006_auto_20210109_2230"),
        ("user_management", "0007_auto_20210110_0050"),
        ("user_management", "0008_auto_20210207_1309"),
    ]

    initial = True

    dependencies = [
        ("auth", "0011_update_proxy_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(blank=True, null=True, verbose_name="last login"),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "email",
                    models.EmailField(max_length=254, unique=True, verbose_name="Email address"),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("first_name", models.CharField(max_length=254, verbose_name="First name")),
                ("last_name", models.CharField(max_length=254, verbose_name="Last name")),
                ("date_of_birth", models.DateField()),
                ("phone", models.CharField(blank=True, max_length=254, null=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Qualification",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("title", models.CharField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name="QualificationGrant",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("expiration_date", models.DateField(blank=True, null=True)),
                (
                    "qualification",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="user_management.qualification",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="userprofile",
            name="calendar_token",
            field=models.CharField(default=secrets.token_urlsafe, max_length=254),
        ),
        migrations.CreateModel(
            name="QualificationCategory",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("uuid", models.UUIDField(default=uuid.uuid4, unique=True)),
                ("title", models.CharField(max_length=254, verbose_name="title")),
            ],
            options={
                "verbose_name": "qualification track",
                "verbose_name_plural": "qualification tracks",
            },
        ),
        migrations.RemoveField(
            model_name="qualificationgrant",
            name="expiration_date",
        ),
        migrations.AddField(
            model_name="qualification",
            name="included_qualifications",
            field=models.ManyToManyField(
                related_name="included_in_set", to="user_management.Qualification"
            ),
        ),
        migrations.AddField(
            model_name="qualification",
            name="uuid",
            field=models.UUIDField(default=None, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="qualificationgrant",
            name="expires",
            field=models.DateTimeField(blank=True, null=True, verbose_name="expiration date"),
        ),
        migrations.AlterField(
            model_name="qualificationgrant",
            name="qualification",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="grants",
                to="user_management.qualification",
            ),
        ),
        migrations.AlterField(
            model_name="qualificationgrant",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="qualification_grants",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="qualification",
            name="category",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="qualifications",
                to="user_management.qualificationcategory",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="qualification",
            name="abbreviation",
            field=models.CharField(default="", max_length=254),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="qualification",
            options={"verbose_name": "qualification", "verbose_name_plural": "qualifications"},
        ),
        migrations.AlterModelOptions(
            name="userprofile",
            options={"verbose_name": "user profile", "verbose_name_plural": "user profiles"},
        ),
        migrations.AlterField(
            model_name="qualification",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="qualifications",
                to="user_management.qualificationcategory",
                verbose_name="category",
            ),
        ),
        migrations.AlterField(
            model_name="qualification",
            name="included_qualifications",
            field=models.ManyToManyField(
                related_name="included_by", to="user_management.Qualification"
            ),
        ),
        migrations.AlterField(
            model_name="qualification",
            name="title",
            field=models.CharField(max_length=254, verbose_name="title"),
        ),
        migrations.AlterField(
            model_name="qualificationgrant",
            name="qualification",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="user_management.qualification",
                verbose_name="qualification",
            ),
        ),
        migrations.AlterField(
            model_name="qualificationgrant",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
                verbose_name="user profile",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="calendar_token",
            field=models.CharField(
                default=secrets.token_urlsafe, max_length=254, verbose_name="calendar token"
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="date_of_birth",
            field=models.DateField(verbose_name="date of birth"),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="email",
            field=models.EmailField(max_length=254, unique=True, verbose_name="email address"),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="first_name",
            field=models.CharField(max_length=254, verbose_name="first name"),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="last_name",
            field=models.CharField(max_length=254, verbose_name="last name"),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="phone",
            field=models.CharField(max_length=254, null=True, verbose_name="phone number"),
        ),
        migrations.AlterField(
            model_name="qualification",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
        migrations.AlterField(
            model_name="qualificationgrant",
            name="qualification",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="grants",
                to="user_management.qualification",
                verbose_name="qualification",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="phone",
            field=models.CharField(
                blank=True, default="", max_length=254, verbose_name="phone number"
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="qualification",
            name="included_qualifications",
            field=models.ManyToManyField(
                blank=True, related_name="included_by", to="user_management.Qualification"
            ),
        ),
        migrations.AlterField(
            model_name="qualificationgrant",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="qualification_grants",
                to=settings.AUTH_USER_MODEL,
                verbose_name="user profile",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="qualificationgrant",
            unique_together={("qualification", "user")},
        ),
        migrations.CreateModel(
            name="WorkingHours",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("hours", models.DecimalField(decimal_places=2, max_digits=7)),
                ("reason", models.CharField(blank=True, default="", max_length=1024)),
                ("datetime", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Consequence",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("slug", models.CharField(max_length=255)),
                ("data", models.JSONField(default=dict)),
                (
                    "state",
                    models.TextField(
                        choices=[
                            ("needs_confirmation", "needs confirmation"),
                            ("executed", "executed"),
                            ("failed", "failed"),
                            ("denied", "denied"),
                        ],
                        default="needs_confirmation",
                        max_length=31,
                    ),
                ),
                ("executed_at", models.DateTimeField(blank=True, null=True)),
                ("fail_reason", models.TextField(blank=True, max_length=255)),
                (
                    "decided_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="confirmed_consequences",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="confirmed by",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="affecting_consequences",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="affected user",
                    ),
                ),
            ],
        ),
        migrations.RunPython(
            code=create_initial_permissions,
        ),
        migrations.RemoveField(
            model_name="workinghours",
            name="datetime",
        ),
        migrations.AddField(
            model_name="workinghours",
            name="date",
            field=models.DateField(default=datetime.date(2021, 1, 9)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="consequence",
            name="data",
            field=models.JSONField(
                decoder=ephios.extra.json.CustomJSONDecoder,
                default=dict,
                encoder=ephios.extra.json.CustomJSONEncoder,
            ),
        ),
        migrations.AlterField(
            model_name="workinghours",
            name="reason",
            field=models.CharField(default="", max_length=1024),
        ),
        migrations.AlterModelTable(
            name="consequence",
            table="consequence",
        ),
        migrations.AlterModelTable(
            name="qualification",
            table="qualification",
        ),
        migrations.AlterModelTable(
            name="qualificationcategory",
            table="qualificationcategory",
        ),
        migrations.AlterModelTable(
            name="qualificationgrant",
            table="qualificationgrant",
        ),
        migrations.AlterModelTable(
            name="userprofile",
            table="userprofile",
        ),
        migrations.AlterModelTable(
            name="workinghours",
            table="workinghours",
        ),
    ]
