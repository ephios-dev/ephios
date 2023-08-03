from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from ephios.modellogging.json import LogJSONDecoder, LogJSONEncoder
from ephios.modellogging.recorders import (
    InstanceActionType,
    capitalize_first,
    recorder_types_by_slug,
)

# pylint: disable=protected-access


class LogEntry(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="logentries",
    )
    content_object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey("content_type", "content_object_id")
    attached_to_object_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="associated_logentries"
    )
    attached_to_object_id = models.PositiveIntegerField(db_index=True)
    attached_to_object = GenericForeignKey("attached_to_object_type", "attached_to_object_id")
    datetime = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="logging_entries",
    )
    action_type = models.CharField(
        max_length=255, choices=[(value, value) for value in InstanceActionType]
    )
    request_id = models.CharField(max_length=36, null=True, blank=True)
    data = models.JSONField(default=dict, encoder=LogJSONEncoder, decoder=LogJSONDecoder)

    class Meta:
        ordering = ("-datetime", "-id")
        verbose_name = _("Log entry")
        verbose_name_plural = _("Log entries")

    @cached_property
    def records(self):
        recorder_types = recorder_types_by_slug(self.content_type.model_class())
        for recorder in self.data.values():
            if not isinstance(recorder, dict) or "slug" not in recorder:
                continue
            yield recorder_types[recorder["slug"]].deserialize(
                recorder["data"], self.content_type.model_class(), self.action_type
            )

    @property
    def content_object_classname(self):
        try:
            return capitalize_first(self.content_type.model_class()._meta.verbose_name)
        except AttributeError:
            return str(self.content_type)

    @property
    def content_object_or_str(self):
        try:
            return self.content_object
        except AttributeError:
            return self.data.get("__str__")

    def __str__(self):
        if self.content_object:
            return f"{self.action_type} {type(self.content_object)._meta.verbose_name} {str(self.content_object)}"
        return f"{self.action_type} {self.content_type.model} {self.content_object_or_str}"
