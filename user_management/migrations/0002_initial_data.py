# Generated by Django 3.0.6 on 2020-08-18 21:05
from datetime import datetime

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations, models
import django.db.models.deletion

from django.contrib.contenttypes.models import ContentType
from guardian.shortcuts import assign_perm


def create_initial_model_instances(apps, schema_editor):
    # This does not use historical models, but the current version of Group and Permission
    # It might break if these models change in the future, which will only happen
    # * on Django Version upgrade
    # * when we introduce custom models

    from django.contrib.auth.models import Group, Permission
    from user_management.models import UserProfile

    group_content_type = ContentType.objects.get_for_model(Group)
    permission = Permission(
        name="Publish event for group",
        codename="publish_event_for_group",
        content_type=group_content_type,
    )
    permission.save()

    user = UserProfile(
        email="admin@localhost",
        first_name="Admin",
        last_name="Localhost",
        date_of_birth=datetime(year=1970, month=1, day=1),
    )

    user.is_staff = True
    user.is_superuser = True
    user.password = make_password("admin")
    user.save()

    helfer = Group.objects.create(name="Helfer")
    helfer.user_set.add(user)
    helfer.save()
    assign_perm(permission, helfer, helfer)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("user_management", "0001_initial"),
        ("guardian", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_initial_model_instances, migrations.RunPython.noop),
    ]
