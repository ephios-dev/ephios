import json

from dynamic_preferences.types import (
    BasePreferenceType,
    BaseSerializer,
    ModelMultipleChoicePreference,
)

from ephios.extra.json import CustomJSONDecoder, CustomJSONEncoder


class CustomModelMultipleChoicePreference(ModelMultipleChoicePreference):
    def _setup_signals(self):
        pass


class DictSerializer(BaseSerializer):
    @classmethod
    def clean_to_db_value(cls, value):
        return json.dumps(value, cls=CustomJSONEncoder)

    @classmethod
    def to_python(cls, value, **kwargs):
        return json.loads(value, cls=CustomJSONDecoder)


class DictPreference(BasePreferenceType):
    serializer = DictSerializer
