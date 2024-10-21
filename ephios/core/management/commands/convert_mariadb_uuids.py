from django.core.management.base import BaseCommand
from django.db import connection, models

# taken from https://github.com/wagtail/wagtail/pull/11912/files licensed under BSD-3
# Django5.0 UUID fields cause Errors with MariaDB 10.7+
# This management command converts old UUID columns to the new format
# see https://github.com/wagtail/wagtail/pull/11912


class Command(BaseCommand):
    help = "Converts UUID columns from char type to the native UUID type used in MariaDB 10.7+ and Django 5.0+."

    def convert_field(self, model, field_name, null=False, unique=False):
        # pylint: disable=protected-access
        if model._meta.get_field(field_name).model != model:
            # Field is inherited from a parent model
            return

        if not model._meta.managed:
            # The migration framework skips unmanaged models, so we should too
            return

        old_field = models.CharField(null=null, max_length=36, unique=unique)
        old_field.set_attributes_from_name(field_name)
        old_field.model = model

        new_field = models.UUIDField(null=null, unique=unique)
        new_field.set_attributes_from_name(field_name)
        new_field.model = model

        with connection.schema_editor() as schema_editor:
            schema_editor.alter_field(model, old_field, new_field)

    def handle(self, *args, **options):
        from ephios.core.models import Qualification, QualificationCategory
        from ephios.plugins.complexsignup.models import BuildingBlock

        self.convert_field(Qualification, "uuid", unique=True)
        self.convert_field(QualificationCategory, "uuid", unique=True)
        self.convert_field(BuildingBlock, "uuid", unique=True)

        from ephios.api.models import IDToken, RefreshToken

        self.convert_field(IDToken, "jti", unique=True)
        self.convert_field(RefreshToken, "token_family", null=True)
