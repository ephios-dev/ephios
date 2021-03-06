# Generated by Django 3.1.6 on 2021-02-19 15:42

from django.db import migrations


def migrate_content_type(apps, schema_editor):
    from django.contrib.contenttypes.models import ContentType

    for obj in ContentType.objects.filter(app_label="user_management"):
        ContentType.objects.filter(app_label="core", model=obj.model).delete()
        obj.app_label = "core"
        obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_merge_content_type_20210208_0020"),
    ]

    operations = [
        migrations.RunPython(migrate_content_type),
    ]
