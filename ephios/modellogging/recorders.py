import itertools
from enum import Enum

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import Signal, receiver
from django.template.defaultfilters import yesno
from django.utils.translation import gettext_lazy as _

# pylint: disable=protected-access


def capitalize_first(string):
    return string[0].upper() + string[1:]


class InstanceActionType(str, Enum):
    CREATE = "create"
    CHANGE = "change"
    DELETE = "delete"


class BaseLogRecorder:
    """
    A field on a model that is incorporated into the Log.
    can concretely be:

    - ModelLoggedChange: for a field that is directly derived from a model field
    - M2MLoggedChange: for adds/removes to a m2m relationship
    - DerivedLoggedChange: for a field that is derived from the instance (use to customize stuff)
    - PermissionLoggedChange: for changes in users and groups having a certain permission on the logged object


    unserializing must be available after model_save was called.
    getting statements must be available after serializing was called.
    """

    slug = NotImplemented

    def model_init(self, instance):
        pass

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

    def serialize(self):
        """
        dump this change to a dict
        """
        raise NotImplementedError

    @classmethod
    def deserialize(cls, data, model):
        """
        load this change from a dict.
        """
        raise NotImplementedError

    def record(self, action: InstanceActionType, instance, db_instance=None):
        """
        Record changes for change action and field state for creation and deletion.
        If action is CHANGE,``db_instance`` is set to an instance freshly fetched from the db.
        """

    def change_statements(self):
        """
        Return a single or multiple human readable statements about the change.
        """
        raise NotImplementedError

    def value_statements(self):
        """
        Return a single or multiple human readable statements about the current value.
        Used for reporting created and deleted instances.
        """


class ModelFieldLogRecorder(BaseLogRecorder):
    slug = "modelfield"

    def __init__(self, field):
        self.field = field

    def record(self, action: InstanceActionType, instance, db_instance=None):
        self.old_value = self.field.value_from_object(db_instance) if db_instance else None
        self.new_value = self.field.value_from_object(instance)

    def is_changed(self):
        return self.old_value != self.new_value

    @property
    def key(self):
        return f"field-{self.field.name}"

    def serialize(self):
        data = {
            "field_name": self.field.name,
            "verbose_name": str(
                getattr(self.field, "verbose_name", capitalize_first(self.field.name))
            ),
            "old_value": self.old_value,
            "new_value": self.new_value,
        }
        if self.field.one_to_one or self.field.many_to_one:
            try:
                data["old_value_str"] = str(
                    self.field.related_model._default_manager.get(pk=self.old_value)
                )
            except self.field.related_model.DoesNotExist:
                pass
            try:
                data["new_value_str"] = str(
                    self.field.related_model._default_manager.get(pk=self.new_value)
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
    def deserialize(cls, data, model):
        try:
            self = cls(model._meta.get_field(data["field_name"]))
        except FieldDoesNotExist:
            self = cls(None)
            self.label = data["verbose_name"]
        else:
            self.label = getattr(self.field, "verbose_name", capitalize_first(self.field.name))

        self.old_value = data["old_value"]
        self.new_value = data["new_value"]

        if self.field is None:
            pass
        elif self.field.one_to_one or self.field.many_to_one:
            try:
                self.old_value = self.field.related_model._default_manager.get(pk=self.old_value)
            except self.field.related_model.DoesNotExist:
                self.old_value = data.get("old_value_str")
            try:
                self.new_value = self.field.related_model._default_manager.get(pk=self.new_value)
            except self.field.related_model.DoesNotExist:
                self.new_value = data["new_value_str"]
        elif getattr(self.field, "choices", None):
            self.old_value = self._choice_to_display(self.old_value)
            self.new_value = self._choice_to_display(self.new_value)
        elif isinstance(self.field, models.BooleanField):
            self.old_value = yesno(self.old_value)
            self.new_value = yesno(self.new_value)

        return self

    def change_statements(self):
        return [f"{self.label}: {self.old_value} → {self.new_value}"]

    def value_statements(self):
        return [f"{self.label}: {self.new_value}"]


class M2MLogRecorder(BaseLogRecorder):
    slug = "m2mfield"

    def __init__(self, field):
        self.field = field
        if field and not field.many_to_many:
            raise ValueError("field is not a many to many field")

        self.added_pks, self.removed_pks = set(), set()

    def record(self, action: InstanceActionType, instance, db_instance=None):
        if action != InstanceActionType.CHANGE:
            self.current = [
                {"pk": obj.pk, "str": str(obj)} for obj in getattr(instance, self.field.name).all()
            ]

    def record_clear(self, instance):
        self.added_pks = set()
        self.removed_pks = {obj.pk for obj in getattr(instance, self.field.name).all()}

    def is_changed(self):
        return bool(self.removed_pks) or bool(self.added_pks)

    @property
    def key(self):
        return f"m2m-{self.field.name}"

    def serialize(self):
        data = {
            "field_name": self.field.name,
            "verbose_name": str(
                getattr(self.field, "verbose_name", capitalize_first(self.field.name))
            ),
        }

        related_objects = {
            obj.pk: obj
            for obj in self.field.related_model._default_manager.filter(
                pk__in={*self.added_pks, *self.removed_pks}
            )
        }

        data["added"] = [{"pk": pk, "str": str(related_objects[pk])} for pk in self.added_pks]
        data["removed"] = [{"pk": pk, "str": str(related_objects[pk])} for pk in self.removed_pks]

        if current := getattr(self, "current", None):
            data["current"] = current

        return data

    @classmethod
    def deserialize(cls, data, model):

        try:
            self = cls(model._meta.get_field(data["field_name"]))
        except FieldDoesNotExist:
            self = cls(None)
            self.label = data["verbose_name"]
            self.added = [obj["str"] for obj in data["added"]]
            self.removed = [obj["str"] for obj in data["removed"]]
            self.current = [obj["str"] for obj in data.get("current", [])]
        else:
            self.label = getattr(self.field, "verbose_name", capitalize_first(self.field.name))
            related_objects = {
                obj.pk: obj
                for obj in self.field.related_model._default_manager.filter(
                    pk__in={
                        obj["pk"]
                        for obj in itertools.chain(
                            data["added"], data["removed"], data.get("current", [])
                        )
                    }
                )
            }
            self.added = [str(related_objects.get(obj["pk"], obj["str"])) for obj in data["added"]]
            self.removed = [
                str(related_objects.get(obj["pk"], obj["str"])) for obj in data["removed"]
            ]
            self.current = [
                str(related_objects.get(obj["pk"], obj["str"])) for obj in data.get("current", [])
            ]
        return self

    def change_statements(self):
        statements = []
        for attr, verb in [("added", _("added")), ("removed", _("removed"))]:
            if (items := getattr(self, attr)) :
                statements.append(
                    "{label} {verb}: {items}".format(
                        label=self.label, verb=verb, items=", ".join(items)
                    )
                )
        return statements

    def value_statements(self):
        if not self.current:
            return []
        return "{label}: {items}".format(label=self.label, items=", ".join(self.current))


@receiver(m2m_changed)
def _m2m_changed(
    sender, instance, action, reverse, model, pk_set, **kwargs
):  # pylint: disable=unused-argument
    from ephios.modellogging.models import LoggedModelMixin

    if reverse:
        return
    if not isinstance(instance, LoggedModelMixin):
        return

    hit = False
    for recorder in instance.log_recorders:
        if recorder.slug != M2MLogRecorder.slug:
            continue
        if getattr(type(instance), recorder.field.name).through == sender:
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
            instance.update_log(InstanceActionType.CHANGE)


register_log_recorders = Signal()


@receiver(register_log_recorders)
def _register_inbuilt_recorders(sender, **kwargs):
    return [
        ModelFieldLogRecorder,
        M2MLogRecorder,
    ]
