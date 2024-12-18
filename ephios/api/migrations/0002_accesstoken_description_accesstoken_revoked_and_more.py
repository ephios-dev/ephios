# Generated by Django 4.1.7 on 2023-05-28 18:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="accesstoken",
            name="description",
            field=models.CharField(blank=True, max_length=1000, verbose_name="Description"),
        ),
        migrations.AddField(
            model_name="accesstoken",
            name="revoked",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="accesstoken",
            name="expires",
            field=models.DateTimeField(null=True),
        ),
    ]
