# Generated by Django 3.1.7 on 2021-04-03 21:48

import django.db.models.deletion
from django.db import migrations, models

import ephios.modellogging.json


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("modellogging", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="logentry",
            options={
                "ordering": ("-datetime", "-id"),
                "verbose_name": "Log entry",
                "verbose_name_plural": "Log entries",
            },
        ),
        migrations.AlterField(
            model_name="logentry",
            name="attached_to_object_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="associated_logentries",
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AlterField(
            model_name="logentry",
            name="content_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="logentries",
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AlterField(
            model_name="logentry",
            name="data",
            field=models.JSONField(
                decoder=ephios.modellogging.json.LogJSONDecoder,
                default=dict,
                encoder=ephios.modellogging.json.LogJSONEncoder,
            ),
        ),
    ]
