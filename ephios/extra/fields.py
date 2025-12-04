import datetime

from django import forms
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

    def __init__(self, **kwargs):
        fields = (
            IntegerField(label=_("Days"), min_value=1, max_value=31),
            IntegerField(label=_("Months"), min_value=1, max_value=12),
            IntegerField(label=_("Years"), min_value=0),
        )
        super().__init__(fields, require_all_fields=False)

    def compress(self, data_list):
        return RelativeTime(days=data_list[0], months=data_list[1], years=data_list[2])
