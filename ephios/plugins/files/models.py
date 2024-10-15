from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from ephios.core.models import Event, UserProfile
from ephios.modellogging.log import ModelFieldsLogConfig, register_model_for_logging


class Document(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    file = models.FileField(
        upload_to="documents/", validators=[FileExtensionValidator(["pdf"])], verbose_name=_("File")
    )
    attached_to = models.ManyToManyField(
        Event, related_name="documents", verbose_name=_("Attached to")
    )
    uploader = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name=_("Uploader"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Last modified"))

    def __str__(self):
        return str(self.title)


register_model_for_logging(
    Document,
    ModelFieldsLogConfig(
        unlogged_fields=["id", "file", "updated_at"],
    ),
)
