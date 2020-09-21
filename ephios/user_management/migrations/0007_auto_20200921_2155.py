# Generated by Django 3.1.1 on 2020-09-21 19:55

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("user_management", "0006_auto_20200829_2348"),
    ]

    operations = [
        migrations.AlterField(
            model_name="qualification",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
        migrations.AlterField(
            model_name="qualificationcategory",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
