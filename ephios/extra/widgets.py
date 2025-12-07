import re

from dateutil.rrule import rrulestr
from django import forms
from django.core.exceptions import ValidationError
from django.forms import CharField, DateInput, MultiWidget, Textarea, TimeInput
from django.forms.utils import to_current_timezone
from django.utils.translation import gettext as _

from ephios.extra.relative_time import RelativeTime


class CustomDateInput(DateInput):
    template_name = "extra/widgets/custom_date_input.html"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%d")
        super().__init__(*args, **kwargs)


class CustomTimeInput(TimeInput):
    template_name = "extra/widgets/custom_time_input.html"


class CustomSplitDateTimeWidget(MultiWidget):
    """
    A widget that splits datetime input into two <input type="text"> boxes.
    To be used with a SplitDateTimeField.
    """

    supports_microseconds = False
    template_name = "extra/widgets/custom_split_date_time_widget.html"

    def __init__(self, *args, **kwargs):
        widgets = (
            CustomDateInput(format="%Y-%m-%d", attrs={"class": "form-control"}),
            CustomTimeInput(format="%H:%M", attrs={"class": "form-control"}),
        )
        super().__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        if value:
            value = to_current_timezone(value)
            return [value.date(), value.time()]
        return [None, None]


class RecurrenceWidget(Textarea):
    template_name = "extra/widgets/recurrence_picker.html"

    def __init__(self, *args, **kwargs):
        self.pick_hour = kwargs.pop("pick_hour", False)
        self.original_start = kwargs.pop("original_start", None)
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["pick_hour"] = self.pick_hour
        context["widget"]["original_start"] = self.original_start
        return context


class RecurrenceField(CharField):
    widget = RecurrenceWidget

    def __init__(self, *args, pick_hour=False, original_start=None, **kwargs):
        self.widget = RecurrenceWidget(pick_hour=pick_hour, original_start=original_start)
        super().__init__(*args, **kwargs)

    def clean(self, value):
        try:
            return rrulestr(value, ignoretz=True)
        except (TypeError, KeyError, ValueError) as e:
            raise ValidationError(_("Invalid recurrence rule: {error}").format(error=e)) from e


class RelativeTimeWidget(MultiWidget):
    template_name = "extra/widgets/relative_time_field.html"

    def __init__(self, *args, **kwargs):
        widgets = [
            forms.Select(
                choices=[
                    ("no_expiration", _("No expiration")),
                    ("after_years", _("After X years")),
                    ("date_after_years", _("At set date after X years")),
                ],
                attrs={
                    "class": "form-select",
                    "label": _("Type"),
                    "aria-label": _("Type"),
                },
            ),
            forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "label": _("At day"),
                }
            ),
            forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "label": _("in month"),
                }
            ),
            forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "label": _("after years"),
                }
            ),
        ]

        super().__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        if isinstance(value, RelativeTime):
            if re.match(r"^\+(\d+)$", value.year) and not (value.month and value.day):
                return ["after_years", None, None, value.year.strip("+")]
            elif re.match(r"^\+(\d+)$", value.year) and value.month and value.day:
                return ["date_after_years", value.day, value.month, value.year.strip("+")]
        return [None, None, None, None]


class MarkdownTextarea(forms.Textarea):
    """
    Textarea widget that might be extended in the future
    to add markdown-specific features.

    Markdown source can be rendered in templates using the `rich_text` filter.
    """
