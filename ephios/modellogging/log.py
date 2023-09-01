import contextvars
import itertools
from typing import Dict

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_init, post_save, pre_delete, pre_save
from django.dispatch import receiver

from ephios.modellogging.models import LogEntry
from ephios.modellogging.recorders import InstanceActionType, M2MLogRecorder, ModelFieldLogRecorder

# pylint: disable=protected-access


class BaseLogConfig:
    def initial_log_recorders(self, instance):
        """
        Initial log recorders are always added after model __init__.
        Therefore, recorders added here should not do any db operations.
        If you need those, add them manually, e.g. at the beginning of a form's save().
        """
        return []

    def related_logentries(self, instance):
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

    def save_logentry(self, logentry: LogEntry):
        """
        Save the logentry. Overwrite this method to process the logentry
        bevore saving.
        """
        logentry.save()


class ModelFieldsLogConfig(BaseLogConfig):
    def __init__(self, unlogged_fields=None, attach_to_func=None, initial_recorders_func=None):
        """
        ``unlogged_fields``: Specify a list of field names so that these fields don't get logged.
        Other fields get logged. Defaults to ['id']

        ``attach_to_func``: Specify a function receiving an instance and returning a tuple
        of model class and object pk to attach log entries to.
        Defaults to the instance's class and its own pk.

        ``initial_recorders_func``: Specify a function receiving an instance and returning
        a list of additional log recorders.
        """

        if unlogged_fields is None:
            unlogged_fields = ["id"]
        self.unlogged_fields = unlogged_fields
        self.attach_to_func = attach_to_func
        self.initial_recorders_func = initial_recorders_func

    def object_to_attach_logentries_to(self, instance):
        if self.attach_to_func:
            return self.attach_to_func(instance)
        return super().object_to_attach_logentries_to(instance)

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
        if self.initial_recorders_func:
            yield from self.initial_recorders_func(instance)


log_request = contextvars.ContextVar("Current request")
log_request_id = contextvars.ContextVar("Current request id")

LOGGED_MODELS: Dict[models.Model, BaseLogConfig] = {}


def register_model_for_logging(model_class, config):
    LOGGED_MODELS[model_class] = config


def add_log_recorder(instance, recorder):
    instance._log_recorders.append(recorder)
    recorder.attached(instance)


def _get_log_data(instance, action_type):
    for recorder in instance._log_recorders:
        recorder.record(action_type, instance)

    data = {
        recorder.key: {
            "slug": recorder.slug,
            "data": recorder.serialize(action_type),
        }
        for recorder in instance._log_recorders
        if recorder.is_changed() or action_type != InstanceActionType.CHANGE
    }

    if not data:
        return {}

    try:
        data["__str__"] = str(instance)
    except ObjectDoesNotExist:
        # sometimes, when deleting objects, they are in an invalid state, so str fails
        if not action_type == InstanceActionType.DELETE:
            raise
        data["__str__"] = None
    return data


def update_log(instance, action_type: InstanceActionType):
    logentry = getattr(instance, "_current_logentry", None)
    log_data = _get_log_data(instance, logentry.action_type if logentry else action_type)
    if not log_data:
        return

    config = LOGGED_MODELS[type(instance)]
    if logentry:
        logentry.data.update(log_data)
    else:
        try:
            user = log_request.get(None).user
            if not user.is_authenticated:
                user = None
            request_id = log_request_id.get(None)
        except AttributeError:
            user = None
            request_id = None
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

    config.save_logentry(logentry)
    instance._current_logentry = logentry


@receiver(post_init)
def log_post_init(sender, instance, **kwargs):
    if config := LOGGED_MODELS.get(sender):
        instance._log_recorders = list(config.initial_log_recorders(instance))
        for recorder in instance._log_recorders:
            recorder.attached(instance)


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
    if sender in LOGGED_MODELS:
        update_log(instance, InstanceActionType.DELETE)
