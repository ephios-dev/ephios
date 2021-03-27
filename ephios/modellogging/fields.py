from django.core.exceptions import FieldDoesNotExist

from ephios.modellogging.models import capitalize_first


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

    recorder_slug = NotImplemented

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
    def unserialize(cls, data, model):
        """
        load this change from a dict.
        """
        raise NotImplementedError

    def model_save(self, instance, db_instance):
        pass

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
    recorder_slug = "modelfield"

    def __init__(self, field):
        self.field = field

    def model_save(self, instance, db_instance):
        self.old_value = self.field.value_from_object(db_instance)
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
        }
        if self.field.one_to_one or self.field.many_to_one:
            data.update(
                {
                    "old_value": self.old_value.pk,
                    "old_value_str": str(self.old_value),
                    "new_value": self.new_value.pk,
                    "new_value_str": str(self.new_value),
                }
            )
        else:
            data.update(
                {
                    "old_value": self.old_value,
                    "new_value": self.new_value,
                }
            )
        return data

    @classmethod
    def unserialize(cls, data, model):
        self = cls(None)
        field = None
        try:
            field = model._meta.get_field(data["field_name"])
        except FieldDoesNotExist:
            self.label = data["verbose_name"]
        else:
            self.label = getattr(field, "verbose_name", capitalize_first(field.name))

        self.old_value = data["old_value"]
        self.new_value = data["new_value"]
        if self.field.one_to_one or self.field.many_to_one:
            try:
                self.old_value = field.related_model._default_manager.get(pk=self.old_value)
            except field.related_model.DoesNotExist:
                self.old_value = data["old_value_str"]
            try:
                self.new_value = field.related_model._default_manager.get(pk=self.new_value)
            except field.related_model.DoesNotExist:
                self.new_value = data["new_value_str"]

        return self

    def change_statements(self):
        return [f"{self.label}: {self.old_value} -> {self.new_value}"]

    def value_statements(self):
        return [f"{self.label}: {self.new_value}"]
