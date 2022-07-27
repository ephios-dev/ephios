from urllib.parse import urlparse

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.registries import global_preferences_registry
from dynamic_preferences.types import StringPreference

from ephios.core.dynamic_preferences_registry import general_global_section


@global_preferences_registry.register
class QualificationManagementReposPreference(StringPreference):
    name = "qualification_management_repos"
    verbose_name = _("List of qualification repositories")
    help_text = _("To use multiple repositories, put URLs in separate lines.")
    section = general_global_section
    default = "https://github.com/ephios-dev/ephios-qualification-fixtures/raw/main/de/_all.json"
    widget = forms.Textarea(attrs={"rows": 1})

    def validate(self, value):
        for repo_url in (line.strip() for line in value.split("\n")):
            parts = urlparse(repo_url)
            if parts.path.endswith(".json") and parts.scheme.startswith("http") and parts.netloc:
                continue
            raise ValidationError(_("'{url}' does not look like a repo url.").format(url=repo_url))
