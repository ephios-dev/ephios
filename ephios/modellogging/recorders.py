import itertools
from enum import Enum
from typing import Callable

from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import Signal, receiver
from django.template.defaultfilters import yesno
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import get_users_with_perms

from ephios.extra.permissions import get_groups_with_perms

# pylint: disable=protected-access


def capitalize_first(string):
    return string[0].upper() + string[1:]


class InstanceActionType(str, Enum):
    CREATE = "create"
    CHANGE = "change"
    DELETE = "delete"


class BaseLogRecorder:
    """
    A Log Recorder is used to record changes made to a model instance that can later be included in a log entry.
    A recorder follows a strict lifecycle:
        - creation at model instance initialisation or later
        - getting ``attached`` to an instance
        - ``record``ing a change from an instance and the way it exists in the db, or just saving the current state
        - ``is_changed`` is called to find out whether the recorder should be included in the log
        - ``key`` is used to merge multiple log entries into one, should there be multiple ``save`` calls
        - ``serialize`` is called to save the state into json. The ``slug`` is then added to later identify the corresponding Recorder class.
        - ``deserialize`` is called when we want to display a recorder's recordings after some time.
          deserialized recorders will never be serialized again, as e.g. a model field might not exist anymore
        - ``change_statements`` (for change action) and ``value_statements`` (for create and delete action)
           then return dicts to be fed into a statement template.

    Statement templates accept a ``label`` value, an optional ``verb``, and either an ``objects`` list or
    a ``value`` with - optionally - an additional ``old_value``.
    """

    slug = NotImplemented

    def attached(self, instance):
        pass

    def record(self, action: InstanceActionType, instance):
        """
        Record changes for change action and field state for creation and deletion.
        If action is CHANGE,``db_instance`` is set to an instance freshly fetched from the db.
        """

    def is_changed(self):
        """
        Returns whether the values have changed and should be included in the log.
        """
        raise NotImplementedError

    @property
    def key(self):
        """
        Some key to identify the field
        """
        raise NotImplementedError

    def serialize(self, action_type: InstanceActionType):
        """
        dump this change to a dict
        """
        raise NotImplementedError

    @classmethod
    def deserialize(cls, data, model, action_type: InstanceActionType):
        """
        load this change from a dict.
        """
        raise NotImplementedError

    def change_statements(self):
        """
        Yield human readable statements for reporting about changes.
        """
        raise NotImplementedError

    def value_statements(self):
        """
        Yield human readable statements about the current value.
        Used for reporting about created and deleted instances.
        """
        raise NotImplementedError


class ModelFieldLogRecorder(BaseLogRecorder):
    slug = "modelfield"

    def __init__(self, field):
        self.field = field

    def attached(self, instance):
        # is id for foreign keys
        self.old_value = self.field.value_from_object(instance)

    def record(self, action: InstanceActionType, instance):
        if self.field.one_to_one or self.field.many_to_one:
            # actual object for foreign keys
            try:
                self.new_value = getattr(instance, self.field.name)
            except ObjectDoesNotExist:
                self.new_value = None
        else:
            self.new_value = self.field.value_from_object(instance)

    def is_changed(self):
        if self.field.one_to_one or self.field.many_to_one:
            return self.old_value != getattr(self.new_value, "pk", None)
        return self.old_value != self.new_value

    @property
    def key(self):
        return f"field-{self.field.name}"

    def serialize(self, action_type: InstanceActionType):
        data = {
            "field_name": self.field.name,
            "verbose_name": str(
                getattr(self.field, "verbose_name", capitalize_first(self.field.name))
            ),
            "old_value": self.old_value,
            "new_value": self.new_value,
        }
        if self.field.one_to_one or self.field.many_to_one:
            if not self.is_changed():
                data["old_value"] = self.new_value
            elif self.old_value:
                try:
                    data["old_value"] = self.field.related_model._base_manager.get(
                        pk=self.old_value
                    )
                except self.field.related_model.DoesNotExist:
                    pass
        return data

    def _choice_to_display(self, choice):  # does not support nested choices
        for key, label in self.field.choices:
            if key == choice:
                return label
        return choice

    @classmethod
    def deserialize(cls, data, model, action_type: InstanceActionType):
        try:
            self = cls(model._meta.get_field(data["field_name"]))
        except (FieldDoesNotExist, AttributeError):
            self = cls(None)
            self.label = data["verbose_name"]
        else:
            self.label = getattr(self.field, "verbose_name", capitalize_first(self.field.name))

        self.old_value = data["old_value"]
        self.new_value = data["new_value"]

        if self.field is None:
            pass
        elif self.field.one_to_one or self.field.many_to_one:
            pass
        elif getattr(self.field, "choices", None):
            self.old_value = self._choice_to_display(self.old_value)
            self.new_value = self._choice_to_display(self.new_value)
        elif isinstance(self.field, models.BooleanField):
            self.old_value = yesno(self.old_value)
            self.new_value = yesno(self.new_value)

        return self

    def change_statements(self):
        yield {"label": self.label, "value": self.new_value, "old_value": self.old_value}

    def value_statements(self):
        yield {"label": self.label, "value": self.new_value}


class M2MLogRecorder(BaseLogRecorder):
    # pylint: disable=too-many-instance-attributes

    slug = "m2mfield"

    def __init__(self, field, reverse=False, verbose_name=None):
        if reverse and not verbose_name:
            raise ValueError("You must provide a verbose name when reversing m2m relationships.")

        self.field = field
        self.reversed = reverse
        self.verbose_name = verbose_name
        if field and not self.verbose_name:
            self.verbose_name = str(getattr(field, "verbose_name", capitalize_first(field.name)))
        self.added_pks, self.removed_pks = set(), set()

    def attached(self, instance):
        self.model = type(instance)

    @property
    def field_name(self):
        return self.field.remote_field.related_name if self.reversed else self.field.name

    def record(self, action: InstanceActionType, instance):
        if action != InstanceActionType.CHANGE:
            self.current = list(getattr(instance, self.field_name).all())

    def record_clear(self, instance):
        self.added_pks = set()
        self.removed_pks = {obj.pk for obj in getattr(instance, self.field_name).all()}

    def is_changed(self):
        return bool(self.removed_pks) or bool(self.added_pks)

    @property
    def key(self):
        return f"m2m-{self.field.name}"

    def serialize(self, action_type: InstanceActionType):
        related_model = self.field.model if self.reversed else self.field.related_model
        data = {
            "field_name": self.field_name,
            "verbose_name": self.verbose_name,
            "added": related_model._base_manager.filter(pk__in=self.added_pks),
            "removed": related_model._base_manager.filter(pk__in=self.removed_pks),
        }

        if current := getattr(self, "current", None):
            data["current"] = current

        return data

    @classmethod
    def deserialize(cls, data, model, action_type: InstanceActionType):
        try:
            self = cls(model._meta.get_field(data["field_name"]))
        except (AttributeError, FieldDoesNotExist):
            self = cls(None)
            self.label = data["verbose_name"]
        else:
            self.label = getattr(self.field, "verbose_name", capitalize_first(self.field.name))
        self.added = data["added"]
        self.removed = data["removed"]
        self.current = data.get("current", [])
        return self

    def change_statements(self):
        for attr, verb in [("added", _("added")), ("removed", _("removed"))]:
            if objects := getattr(self, attr):
                yield {"label": self.label, "verb": verb, "objects": objects}

    def value_statements(self):
        if self.current:
            yield {"label": self.label, "objects": self.current}


@receiver(m2m_changed)
def _m2m_changed(
    sender, instance, action, reverse, model, pk_set, **kwargs
):  # pylint: disable=unused-argument
    from ephios.modellogging.log import LOGGED_MODELS, update_log

    if "pre" not in action:
        return

    if type(instance) not in LOGGED_MODELS:
        return

    hit = False
    for recorder in instance._log_recorders:
        if recorder.slug != M2MLogRecorder.slug:
            continue
        if getattr(type(instance), recorder.field_name).through == sender:
            if action == "pre_remove":
                recorder.removed_pks |= set(pk_set)
                hit = True
            elif action == "pre_add":
                recorder.added_pks |= set(pk_set)
                hit = True
            elif action == "pre_clear":
                recorder.record_clear(instance)
                hit = True
        if hit:
            update_log(instance, InstanceActionType.CHANGE)


class PermissionLogRecorder(BaseLogRecorder):
    """
    This recorder records users and groups that have object permissions for the logged instance.
    If the logged model is User or Group, consider using the DerivedFieldsLogRecorder to record Permissions.
    """

    # pylint: disable=too-many-instance-attributes
    slug = "permission-recorder"

    def __init__(self, codename, label):
        self.codename = codename
        self.label = label

    def attached(self, instance):
        self.old_users = set(
            get_users_with_perms(
                instance, with_group_users=False, only_with_perms_in=[self.codename]
            )
        )
        self.old_groups = set(get_groups_with_perms(instance, only_with_perms_in=[self.codename]))

    def record(self, action: InstanceActionType, instance):
        self.new_users = set(
            get_users_with_perms(
                instance, with_group_users=False, only_with_perms_in=[self.codename]
            )
        )
        self.new_groups = set(get_groups_with_perms(instance, only_with_perms_in=[self.codename]))

    def is_changed(self):
        return self.new_groups != self.old_groups or self.new_users != self.old_users

    @property
    def key(self):
        return f"permission-{self.codename}"

    def serialize(self, action_type: InstanceActionType):
        data = {
            "label": str(self.label),
            "codename": self.codename,
        }

        if action_type == InstanceActionType.CHANGE:
            data["added_users"] = self.new_users - self.old_users
            data["removed_users"] = self.old_users - self.new_users
            data["added_groups"] = self.new_groups - self.old_groups
            data["removed_groups"] = self.old_groups - self.new_groups
        else:
            data["users"] = self.new_users
            data["groups"] = self.new_groups

        return data

    @classmethod
    def deserialize(cls, data, model, action_type: InstanceActionType):
        self = cls(data["codename"], data["label"])
        if action_type == InstanceActionType.CHANGE:
            self.added = list(map(str, itertools.chain(data["added_groups"], data["added_users"])))
            self.removed = list(
                map(str, itertools.chain(data["removed_groups"], data["removed_users"]))
            )
        else:
            self.current = list(map(str, itertools.chain(data["groups"], data["users"])))

        return self

    def change_statements(self):
        for attr, verb in [("added", _("added")), ("removed", _("removed"))]:
            if objects := getattr(self, attr):
                yield {"label": self.label, "verb": verb, "objects": objects}

    def value_statements(self):
        if hasattr(self, "current"):
            yield {"label": self.label, "objects": self.current}


class DerivedFieldsLogRecorder(BaseLogRecorder):
    """
    This recorder lets you provide a ``derive`` function you can use to derive fields for the log from the instance.
    Return value must be a dict mapping human readable labels to values.
    """

    slug = "derived-fields"

    def __init__(self, derive: Callable):
        self.derive = derive

    def attached(self, instance):
        self.old_dict = self.derive(instance)

    def record(self, action: InstanceActionType, instance):
        self.new_dict = self.derive(instance)

    def is_changed(self):
        return self.old_dict != self.new_dict

    @property
    def key(self):
        return f"derived-{id(self.derive)}"

    def serialize(self, action_type: InstanceActionType):
        return {
            "changes": {
                str(key): [old_value, new_value]
                for key in set(itertools.chain(self.old_dict.keys(), self.new_dict.keys()))
                if (old_value := self.old_dict.get(key)) != (new_value := self.new_dict.get(key))
                or action_type != InstanceActionType.CHANGE
            }
        }

    @classmethod
    def deserialize(cls, data, model, action_type: InstanceActionType):
        self = cls(None)
        self.changes = data["changes"]

        def prettify(value):
            if isinstance(value, bool):
                return yesno(value)
            if isinstance(value, (list, set)):
                return ", ".join(map(str, value))
            return value

        for key in self.changes:
            old, new = self.changes[key]
            self.changes[key] = [prettify(old), prettify(new)]
        return self

    def change_statements(self):
        for label, (old_value, new_value) in self.changes.items():
            yield {"label": label, "value": new_value, "old_value": old_value}

    def value_statements(self):
        for label, (__, new_value) in self.changes.items():
            yield {"label": label, "value": new_value}


class FixedMessageLogRecorder(BaseLogRecorder):
    slug = "fixed-message"

    def __init__(self, label, message, show_change_statement=True, show_value_statement=False):
        self.label = str(label)
        self.message = str(message)
        self.show_change_statement = show_change_statement
        self.show_value_statement = show_value_statement

    def is_changed(self):
        return True

    @property
    def key(self):
        return f"fixed-{id(self.label + self.message)}"

    def serialize(self, action_type: InstanceActionType):
        return self.__dict__

    @classmethod
    def deserialize(cls, data, model, action_type: InstanceActionType):
        return cls(**data)

    def change_statements(self):
        if self.show_change_statement:
            yield {"label": self.label, "value": self.message}

    def value_statements(self):
        if self.show_value_statement:
            yield {"label": self.label, "value": self.message}


register_log_recorders = Signal()


@receiver(register_log_recorders)
def _register_inbuilt_recorders(sender, **kwargs):
    return [
        ModelFieldLogRecorder,
        M2MLogRecorder,
        PermissionLogRecorder,
        DerivedFieldsLogRecorder,
        FixedMessageLogRecorder,
    ]


def recorder_types_by_slug(model):
    return {
        recorder.slug: recorder
        for recorder in itertools.chain(
            *(recorders for __, recorders in register_log_recorders.send(model))
        )
    }
