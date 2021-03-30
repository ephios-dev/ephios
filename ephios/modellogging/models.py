import itertools
import threading
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.functional import SimpleLazyObject, cached_property
from django.utils.translation import gettext_lazy as _

from ephios.modellogging.json import LogJSONDecoder, LogJSONEncoder
from ephios.modellogging.recorders import (
    InstanceActionType,
    M2MLogRecorder,
    ModelFieldLogRecorder,
    capitalize_first,
    register_log_recorders,
)

# pylint: disable=protected-access


def recorder_types_by_slug(model):
    return {
        recorder.slug: recorder
        for recorder in itertools.chain(
            *(recorders for __, recorders in register_log_recorders.send(model))
        )
    }


class LogEntry(models.Model):
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="logs_about_me"
    )
    content_object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey("content_type", "content_object_id")
    attached_to_object_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="logs_for_me"
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
        return [
            recorder_types[slug].deserialize(
                data, self.content_type.model_class(), self.action_type
            )
            for data in self.data.values()
            if (slug := data.get("slug"))
        ]

    @property
    def message(self):
        if self.action_type == InstanceActionType.CHANGE:
            if self.content_object:
                message = _("{cls} {obj} was changed.")
            else:  # content_object might be deleted
                message = _("{cls} was changed.")
        elif self.action_type == InstanceActionType.CREATE:
            if self.content_object:
                message = _("{cls} {obj} was created.")
            else:
                message = _("{cls} was created.")
        elif self.action_type == InstanceActionType.DELETE:
            message = _("{cls} was deleted.")

        return message.format(
            cls=capitalize_first(self.content_type.model_class()._meta.verbose_name),
            obj=f'"{str(self.content_object)}"' if self.content_object else "",
        )


class LoggedModelMixin(models.Model if TYPE_CHECKING else object):
    thread = threading.local()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_logentry = None
        self.log_recorders = []
        for recorder in self.initial_log_recorders():
            self.add_log_recorder(recorder)

    def add_log_recorder(self, recorder):
        self.log_recorders.append(recorder)
        recorder.attached(self)

    def initial_log_recorders(self):
        opts = self._meta
        for f in itertools.chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
            if not getattr(f, "editable", False):
                continue
            if f.name in self.unlogged_fields:
                continue
            if f.many_to_many:
                yield M2MLogRecorder(f)
            else:
                yield ModelFieldLogRecorder(f)

    def _get_log_data(self, action_type):
        if action_type == InstanceActionType.CHANGE:
            # for this action, we provide a lazily fetched version of the instance as it is stored in the db.
            def get_db_instance():
                db_instance = type(self)(pk=self.pk)
                db_instance.refresh_from_db()
                return db_instance

            db_instance = SimpleLazyObject(get_db_instance)
        else:
            db_instance = None

        for recorder in self.log_recorders:
            recorder.record(action_type, self, db_instance)

        return {
            recorder.key: {**recorder.serialize(action_type), "slug": recorder.slug}
            for recorder in self.log_recorders
            if recorder.is_changed() or action_type != InstanceActionType.CHANGE
        }

    def update_log(self, action_type: InstanceActionType):
        log_data = self._get_log_data(action_type)
        if not log_data:
            return

        if not self._current_logentry or action_type != self._current_logentry.action_type:
            try:
                user = self.thread.request.user
                if not user.is_authenticated:
                    user = None
                request_id = self.thread.request_id
            except AttributeError:
                user = None
                request_id = None
            attach_to_model, attached_to_object_id = self.object_to_attach_logentries_to
            attached_to_object_type = ContentType.objects.get_for_model(attach_to_model)
            self._current_logentry = LogEntry(
                content_object=self,
                attached_to_object_type=attached_to_object_type,
                attached_to_object_id=attached_to_object_id,
                user=user,
                request_id=request_id,
                action_type=action_type,
                data=log_data,
            )
        else:
            recorder_types = recorder_types_by_slug(type(self))
            for key, new_data in log_data.items():
                if (
                    (old_data := self._current_logentry.data.get(key))
                    and new_data["slug"] == old_data["slug"]
                    and (recorder := recorder_types.get(new_data["slug"]))
                ):
                    self._current_logentry.data[key] = recorder.merge_data(
                        old_data, new_data, self._current_logentry.action_type
                    )
                else:
                    self._current_logentry.data[key] = new_data

        self._current_logentry.save()

    def save(self, *args, **kw):
        # Are we creating a new instance?
        # https://docs.djangoproject.com/en/3.0/ref/models/instances/#customizing-model-loading
        if self._state.adding or not self.pk:
            # we need to attach a logentry to an existing object, so we save this newly created instance first
            super().save(*args, **kw)
            self.update_log(InstanceActionType.CREATE)
        else:
            # when saving an existing instance, we get changes by comparing to the version from the database
            # therefore we save the instance after building the logentry
            self.update_log(InstanceActionType.CHANGE)
            super().save(*args, **kw)

    def delete(self, *args, **kw):
        self.update_log(InstanceActionType.DELETE)
        self.related_logentries().delete()
        super().delete(*args, **kw)

    def related_logentries(self):
        """
        Return a queryset with all logentries that should be shown with this model.
        """
        return LogEntry.objects.filter(
            attached_to_object_type=ContentType.objects.get_for_model(type(self)),
            attached_to_object_id=self.pk,
        )

    def grouped_logentries(self):
        """
        Returns a list of lists of logentries for display. The order is not changed.
        Logentries are grouped if they have a matching request_id.
        """
        yield from (
            list(group)
            for key, group in itertools.groupby(
                self.related_logentries().select_related("user"),
                lambda entry: entry.request_id or entry.pk,
            )
        )

    @property
    def object_to_attach_logentries_to(self):
        """
        Return a model class and primary key for the object for which this logentry should be shown.
        By default, show it to the object described by the logentry itself.

        Returning the model instance directly might rely on fetching that object from the database,
        which can break bulk loading in some cases, so we don't do that.
        """
        return type(self), self.pk

    @property
    def unlogged_fields(self):
        """Specify a list of field names so that these fields don't get logged."""
        return ["id"]
