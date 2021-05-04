# Generated by Django 3.1.7 on 2021-04-03 21:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_auto_20210403_2348"),
        ("eventautoqualification", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="eventautoqualificationconfiguration",
            options={"verbose_name": "event auto qualification configuration"},
        ),
        migrations.AlterField(
            model_name="eventautoqualificationconfiguration",
            name="mode",
            field=models.IntegerField(
                choices=[(1, "any shift"), (2, "every shift"), (3, "last shift")],
                default=1,
                verbose_name="Required attendance",
            ),
        ),
        migrations.AlterField(
            model_name="eventautoqualificationconfiguration",
            name="qualification",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="core.qualification",
                verbose_name="Qualification",
            ),
        ),
    ]
