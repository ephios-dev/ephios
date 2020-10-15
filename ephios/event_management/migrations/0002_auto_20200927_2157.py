# Generated by Django 3.1.1 on 2020-09-27 19:57
import json

from django.db import migrations, models

import ephios.extra.json
from ephios.extra.json import CustomJSONDecoder


def unstring_configuration(apps, schema_editor):
    Shift = apps.get_model("event_management", "shift")
    # we switched to json field but were still storing the configuration as a string
    for shift in Shift.objects.all():
        shift.signup_configuration = json.loads(shift.signup_configuration, cls=CustomJSONDecoder)
        shift.save(update_fields=["signup_configuration"])


class Migration(migrations.Migration):
    dependencies = [
        ("event_management", "0001_squashed_0009_auto_20200921_2155"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shift",
            name="signup_configuration",
            field=models.JSONField(
                decoder=ephios.extra.json.CustomJSONDecoder,
                default=dict,
                encoder=ephios.extra.json.CustomJSONEncoder,
            ),
        ),
        migrations.RunPython(unstring_configuration),
    ]
