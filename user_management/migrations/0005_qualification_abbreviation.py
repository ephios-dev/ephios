# Generated by Django 3.0.6 on 2020-08-29 13:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_management", "0004_auto_20200829_1535"),
    ]

    operations = [
        migrations.AddField(
            model_name="qualification",
            name="abbreviation",
            field=models.CharField(default="", max_length=254),
            preserve_default=False,
        ),
    ]
