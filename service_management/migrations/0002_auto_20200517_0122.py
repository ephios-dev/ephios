# Generated by Django 3.0.6 on 2020-05-16 23:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("service_management", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("user_management", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="resourceposition",
            name="qualification",
            field=models.ManyToManyField(
                blank=True, to="user_management.Qualification"
            ),
        ),
        migrations.AddField(
            model_name="resource",
            name="positions",
            field=models.ManyToManyField(to="service_management.ResourcePosition"),
        ),
        migrations.AddField(
            model_name="participation",
            name="resource_position",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="service_management.ResourcePosition",
            ),
        ),
        migrations.AddField(
            model_name="participation",
            name="shift",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="service_management.Shift",
            ),
        ),
        migrations.AddField(
            model_name="participation",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddConstraint(
            model_name="participation",
            constraint=models.UniqueConstraint(
                fields=("user", "shift"), name="unique_shift_participation"
            ),
        ),
    ]
