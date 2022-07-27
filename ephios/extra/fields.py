import datetime

from django import forms


class EndOfDayDateTimeField(forms.DateTimeField):
    """
    A datetime form field that when used with a date-only widget
    creates a datetime with the time at the end of the given day.
    """

    def to_python(self, value):
        result = super().to_python(value)
        if result is None:
            return result
        return datetime.datetime.max.replace(
            year=result.year,
            month=result.month,
            day=result.day,
        )
