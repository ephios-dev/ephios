# Generated by Django 3.2.3 on 2021-05-28 20:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("modellogging", "0002_auto_20210403_2348"),
    ]

    operations = [
        migrations.AlterField(
            model_name="logentry",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
