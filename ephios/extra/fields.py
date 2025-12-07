import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ChoiceField
from django.forms.fields import IntegerField
from django.forms.utils import from_current_timezone
from django.utils.translation import gettext as _

from ephios.extra.relative_time import RelativeTime
from ephios.extra.widgets import RelativeTimeWidget


class EndOfDayDateTimeField(forms.DateTimeField):
    """
    A datetime form field that when used with a date-only widget
    creates a datetime with the time at the end of the given day.
    """

    def to_python(self, value):
        result = super().to_python(value)
        if result is None:
            return result
        return from_current_timezone(
            datetime.datetime.max.replace(
                year=result.year,
                month=result.month,
                day=result.day,
            )
        )


class RelativeTimeField(forms.MultiValueField):
    require_all_fields = False
    widget = RelativeTimeWidget

    def clean(self, value):
        if value[0] == "after_years" and not value[3]:
            raise ValidationError(_("You must specify a number of years."))
        if value[0] == "date_after_years" and not (value[1] and value[2] and value[3]):
            raise ValidationError(_("You must specify a date and a number of years."))
        return super().clean(value)

    def validate(self, value):
        try:
            value.apply_to(datetime.datetime.now())
        except ValueError:
            raise forms.ValidationError(_("Not a valid date"))

    def __init__(self, **kwargs):
        fields = (
            ChoiceField(
                choices=[
                    ("no_expiration", _("No expiration")),
                    ("after_years", _("After X years")),
                    ("date_after_years", _("At set date after X years")),
                ],
                required=True,
            ),
            IntegerField(label=_("Days"), min_value=1, max_value=31, required=False),
            IntegerField(label=_("Months"), min_value=1, max_value=12, required=False),
            IntegerField(label=_("Years"), min_value=0, required=False),
        )
        super().__init__(fields, require_all_fields=False)

    def compress(self, data_list):
        match data_list[0]:
            case "after_years":
                return RelativeTime(year=f"+{data_list[3]}")
            case "date_after_years":
                return RelativeTime(day=data_list[1], month=data_list[2], year=f"+{data_list[3]}")
        return None
