import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.dynamic_preferences_registry import general_global_section
from ephios.extra.preferences import JSONPreference


@global_preferences_registry.register
class QualificationManagementReposPreference(JSONPreference):
    name = "qualification_management_repos"
    verbose_name = _("List of qualification repositories")
    section = general_global_section
    default = json.dumps(
        [
            "https://github.com/ephios-dev/ephios-qualification-fixtures/raw/main/de/_all.json",
        ]
    )
    widget = forms.Textarea(attrs={"rows": 1})

    def validate(self, value):
        try:
            json_value = json.loads(value)
            if not isinstance(json_value, list) or not all(isinstance(v, str) for v in json_value):
                raise ValidationError(_("The input is not a list of strings."))
        except json.JSONDecodeError as e:
            raise ValidationError(_("The input could not be parsed as json.")) from e
