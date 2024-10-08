# Generated by Django 5.0.8 on 2024-09-12 20:15

import oauth2_provider.models
from django.db import migrations, models
from oauth2_provider.settings import oauth2_settings


def forwards_func(apps, schema_editor):
    """
    Forward migration touches every "old" accesstoken.token which will cause the checksum to be computed.
    Taken from https://github.com/jazzband/django-oauth-toolkit/pull/1491/
    """
    AccessToken = apps.get_model(oauth2_settings.ACCESS_TOKEN_MODEL)
    accesstokens = AccessToken._default_manager.all()  # pylint: disable=protected-access
    for accesstoken in accesstokens:
        accesstoken.save(update_fields=["token_checksum"])


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_application_allowed_origins_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="accesstoken",
            name="token_checksum",
            field=oauth2_provider.models.TokenChecksumField(
                default="", max_length=64, blank=True, null=True
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="refreshtoken",
            name="token_family",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name="accesstoken",
            name="token",
            field=models.TextField(),
        ),
        migrations.RunPython(forwards_func, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="accesstoken",
            name="token_checksum",
            field=oauth2_provider.models.TokenChecksumField(
                blank=False, max_length=64, db_index=True, unique=True
            ),
        ),
    ]
