import json

from django import forms
from dynamic_preferences.types import (
    BasePreferenceType,
    BaseSerializer,
    ModelMultipleChoicePreference,
)

from ephios.extra.json import CustomJSONDecoder, CustomJSONEncoder


class CustomModelMultipleChoicePreference(ModelMultipleChoicePreference):
    def _setup_signals(self):
        pass


class JSONSerializer(BaseSerializer):
    @classmethod
    def clean_to_db_value(cls, value):
        return json.dumps(value, cls=CustomJSONEncoder, ensure_ascii=False)

    @classmethod
    def to_python(cls, value, **kwargs):
        return json.loads(value, cls=CustomJSONDecoder)


class JSONPreference(BasePreferenceType):
    serializer = JSONSerializer
    field_class = forms.CharField
    widget = forms.Textarea
