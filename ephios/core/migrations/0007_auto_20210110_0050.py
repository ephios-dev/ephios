# Generated by Django 3.1.4 on 2021-01-09 23:50

import datetime

from django.db import migrations, models

import ephios.extra.json


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_auto_20210109_2230"),
    ]

    operations = [
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
    ]
