from django.core.validators import FileExtensionValidator
from django.db import models

from ephios.core.models import Event
from ephios.modellogging.log import ModelFieldsLogConfig, register_model_for_logging


class Document(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/", validators=[FileExtensionValidator(["pdf"])])
    attached_to = models.ManyToManyField(Event, related_name="documents")

    def __str__(self):
        return str(self.title)


register_model_for_logging(
    Document,
    ModelFieldsLogConfig(
        unlogged_fields=[
            "id",
            "file",
        ],
    ),
)
