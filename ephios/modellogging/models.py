from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.functional import cached_property

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
    datetime = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="logging_entries",
    )
    action_type = models.CharField(
        max_length=255, choices=[(value, value) for value in InstanceActionType]
    )
    request_id = models.CharField(max_length=36, null=True, blank=True)
    data = models.JSONField(default=dict, encoder=LogJSONEncoder, decoder=LogJSONDecoder)

    class Meta:
        ordering = ("-datetime", "-id")

    @cached_property
    def records(self):
        recorder_types = recorder_types_by_slug(self.content_type.model_class())
        for data in self.data.values():
            yield recorder_types[data["slug"]].deserialize(
                data, self.content_type.model_class(), self.action_type
            )

    @property
    def content_object_classname(self):
        return capitalize_first(self.content_type.model_class()._meta.verbose_name)
