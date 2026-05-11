from django.db import migrations, models

import ephios.modellogging.json


def convert_contenttype_id_to_natural_key(apps, schema_editor):
    LogEntry = apps.get_model("modellogging", "LogEntry")
    # our custom JSONDecoder has been changed to the new format, so it fails to read the existing entries
    LogEntry._meta.get_field("data").decoder = None
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct_cache = {}

    for entry in LogEntry.objects.all():
        changed = False
        data = entry.data
        if not isinstance(data, dict):
            continue
        for obj in _find_model_refs(data):
            if "contenttype_id" in obj and "app_label" not in obj:
                ct_id = obj["contenttype_id"]
                if ct_id not in ct_cache:
                    ct = ContentType.objects.get(pk=ct_id)
                    ct_cache[ct_id] = (ct.app_label, ct.model)
                obj["app_label"], obj["model"] = ct_cache[ct_id]
                changed = True
        if changed:
            entry.data = data
            entry.save()


def _find_model_refs(d):
    if isinstance(d, dict):
        if d.get("__model__") in ("__instance__", "__queryset__"):
            yield d
        for v in d.values():
            yield from _find_model_refs(v)
    elif isinstance(d, list):
        for item in d:
            yield from _find_model_refs(item)


class Migration(migrations.Migration):
    dependencies = [
        ("modellogging", "0005_alter_logentry_datetime"),
    ]

    operations = [
        migrations.RunPython(
            convert_contenttype_id_to_natural_key,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="logentry",
            name="data",
            field=models.JSONField(decoder=ephios.modellogging.json.LogJSONDecoder, default=dict),
        ),
    ]
