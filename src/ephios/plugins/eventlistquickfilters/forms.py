from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from ephios.plugins.eventlistquickfilters.models import EventListQuickFilter


class EventListQuickFilterForm(forms.ModelForm):
    class Meta:
        model = EventListQuickFilter
        fields = ["label", "filter_types", "visible_for_groups", "default_for_groups", "position"]
        widgets = {
            "visible_for_groups": Select2MultipleWidget,
            "default_for_groups": Select2MultipleWidget,
        }

    def clean(self):
        cleaned_data = super().clean()
        self._validate_empty_filter_types_default(cleaned_data)
        return cleaned_data

    def _validate_empty_filter_types_default(self, cleaned_data):
        if "filter_types" not in cleaned_data or cleaned_data["filter_types"]:
            return

        visible_groups = cleaned_data.get("visible_for_groups")
        default_groups = cleaned_data.get("default_for_groups")
        if visible_groups is None or default_groups is None:
            return

        non_default_groups = visible_groups.exclude(pk__in=default_groups.values("pk"))
        if not non_default_groups.exists():
            return

        self.add_error(
            "filter_types",
            _(
                "An empty event type selection means all event types, but it must "
                "be the default for every group that can see this filter. Otherwise, "
                "it is ambiguous with a potential other default filter, which is "
                "also identified by an empty selection. To show all event types "
                "without making this filter the default, select every event type "
                "instead."
            ),
        )
