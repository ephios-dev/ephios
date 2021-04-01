import collections
import itertools
import threading
import typing
from typing import Dict

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_init, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils.functional import SimpleLazyObject

from ephios.modellogging.models import LogEntry
from ephios.modellogging.recorders import (
    BaseLogRecorder,
    InstanceActionType,
    M2MLogRecorder,
    ModelFieldLogRecorder,
)


class BaseLogConfig:
    def initial_log_recorders(self, instance):
        return []

    def related_logentries(self, instance):
        from ephios.modellogging.models import LogEntry

        """
        Return a queryset with all logentries that should be shown with the instance.
        """
        return LogEntry.objects.filter(
            attached_to_object_type=ContentType.objects.get_for_model(type(instance)),
            attached_to_object_id=instance.pk,
        )

    def object_to_attach_logentries_to(self, instance):
        """
        Return a model class and primary key for the object for which the instance's logentry should be shown.
        By default, show it to the object described by the logentry itself.

        Returning the model instance directly might rely on fetching that object from the database,
        which can break bulk loading in some cases, so we don't do that.
        """
        return type(instance), instance.pk


class ModelFieldsLogConfig(BaseLogConfig):
    def __init__(self, unlogged_fields=None):
        """Specify a list of field names so that these fields don't get logged. Other fields get logged."""

        if unlogged_fields is None:
            unlogged_fields = ["id"]
        self.unlogged_fields = unlogged_fields

    def initial_log_recorders(self, instance):
        opts = instance._meta
        for f in itertools.chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
            if not getattr(f, "editable", False):
                continue
            if f.name in self.unlogged_fields:
                continue
            if f.many_to_many:
                yield M2MLogRecorder(f)
            else:
                yield ModelFieldLogRecorder(f)


class LogRequestStorage(threading.local):
    def __init__(self):
        self.clear()

    def clear(self):
        # mapping of model instances to their recorders
        self.request_id = None
        self.request = None
        self.recorders: Dict[models.Model, typing.List[BaseLogRecorder]] = collections.defaultdict(
            list
        )
        self.logentry: Dict[models.Model, LogEntry] = {}


log_request_store = LogRequestStorage()

LOGGED_MODELS: Dict[models.Model, BaseLogConfig] = {}


def register_model_for_logging(model_class, config):
    LOGGED_MODELS[model_class] = config


def add_log_recorder(instance, recorder):
    log_request_store.recorders[instance].append(recorder)
    recorder.attached(instance)


def _get_log_data(instance, action_type):
    if action_type == InstanceActionType.CHANGE:
        # for this action, we provide a lazily fetched version of the instance as it is stored in the db.
        def get_db_instance():
            db_instance = type(instance)(pk=instance.pk)
            db_instance.refresh_from_db()
            return db_instance

        db_instance = SimpleLazyObject(get_db_instance)
    else:
        db_instance = None

    for recorder in log_request_store.recorders[instance]:
        recorder.record(action_type, instance, db_instance)

    return {
        recorder.key: {**recorder.serialize(action_type), "slug": recorder.slug}
        for recorder in log_request_store.recorders[instance]
        if recorder.is_changed() or action_type != InstanceActionType.CHANGE
    }


def update_log(instance, action_type: InstanceActionType):
    log_data = _get_log_data(instance, action_type)
    if not log_data:
        return

    # log entries are merged if
    # * a log etnry for this object, from this request, already exists
    # * they don't have any recorder keys in common
    # * action types match

    logentry = log_request_store.logentry.get(instance)

    if (
        logentry
        and action_type == logentry.action_type
        and not (set(logentry.data.keys()) & set(log_data.keys()))
    ):
        logentry.data.update(log_data)
    else:
        try:
            user = log_request_store.request.user
            if not user.is_authenticated:
                user = None
            request_id = log_request_store.request_id
        except AttributeError:
            user = None
            request_id = None
        config = LOGGED_MODELS[type(instance)]
        attach_to_model, attached_to_object_id = config.object_to_attach_logentries_to(instance)
        attached_to_object_type = ContentType.objects.get_for_model(attach_to_model)
        logentry = LogEntry(
            content_object=instance,
            attached_to_object_type=attached_to_object_type,
            attached_to_object_id=attached_to_object_id,
            user=user,
            request_id=request_id,
            action_type=action_type,
            data=log_data,
        )
    logentry.save()


@receiver(post_init)
def log_post_init(sender, instance, **kwargs):
    if config := LOGGED_MODELS.get(sender):
        log_request_store.recorders[instance].extend(config.initial_log_recorders(instance))


@receiver(pre_save)
def log_pre_save(sender, instance, raw, **kwargs):
    if instance.pk and not raw and sender in LOGGED_MODELS:
        update_log(instance, InstanceActionType.CHANGE)


@receiver(post_save)
def log_post_save(sender, instance, created, raw, **kwargs):
    if created and not raw and sender in LOGGED_MODELS:
        update_log(instance, InstanceActionType.CREATE)


@receiver(pre_delete)
def log_pre_delete(sender, instance, **kwargs):
    if config := LOGGED_MODELS.get(sender):
        update_log(instance, InstanceActionType.DELETE)
        config.related_logentries(instance).delete()
