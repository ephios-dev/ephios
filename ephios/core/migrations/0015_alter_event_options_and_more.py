# Generated by Django 4.1.5 on 2023-01-11 13:18

import django.db.models.deletion
from django.db import migrations, models

import ephios.core.models.events


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("core", "0014_auto_20211106_1852"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="event",
            options={
                "base_manager_name": "all_objects",
                "default_manager_name": "objects",
                "permissions": [],
                "verbose_name": "event",
                "verbose_name_plural": "events",
            },
        ),
        migrations.AlterField(
            model_name="abstractparticipation",
            name="polymorphic_ctype",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="polymorphic_%(app_label)s.%(class)s_set+",
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AlterField(
            model_name="abstractparticipation",
            name="shift",
            field=models.ForeignKey(
                on_delete=ephios.core.models.events.NON_POLYMORPHIC_CASCADE,
                related_name="participations",
                to="core.shift",
                verbose_name="shift",
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="core.eventtype",
                verbose_name="event type",
            ),
        ),
        migrations.AlterField(
            model_name="eventtypepreference",
            name="instance",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="core.eventtype"
            ),
        ),
        migrations.AlterField(
            model_name="localparticipation",
            name="abstractparticipation_ptr",
            field=models.OneToOneField(
                auto_created=True,
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                serialize=False,
                to="core.abstractparticipation",
            ),
        ),
        migrations.AlterField(
            model_name="qualification",
            name="abbreviation",
            field=models.CharField(max_length=254, verbose_name="Abbreviation"),
        ),
        migrations.AlterField(
            model_name="qualification",
            name="includes",
            field=models.ManyToManyField(
                blank=True,
                help_text="other qualifications that this qualification includes",
                related_name="included_by",
                to="core.qualification",
                verbose_name="Included",
            ),
        ),
        migrations.AlterField(
            model_name="workinghours",
            name="hours",
            field=models.DecimalField(decimal_places=2, max_digits=7, verbose_name="Hours of work"),
        ),
        migrations.AlterField(
            model_name="workinghours",
            name="reason",
            field=models.CharField(default="", max_length=1024, verbose_name="Occasion"),
        ),
    ]
