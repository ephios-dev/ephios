from django.forms import DateInput, MultiWidget, SplitDateTimeWidget, TimeInput
from django.forms.utils import to_current_timezone


class CustomDateInput(DateInput):
    template_name = "core/fragments/custom_date_input.html"


class CustomTimeInput(TimeInput):
    template_name = "core/fragments/custom_time_input.html"


class CustomSplitDateTimeInput(SplitDateTimeWidget):
    pass


class CustomSplitDateTimeWidget(MultiWidget):
    """
    A widget that splits datetime input into two <input type="text"> boxes.
    """

    supports_microseconds = False
    template_name = "core/fragments/custom_split_date_time_widget.html"

    def __init__(self, *args, **kwargs):
        widgets = (
            CustomDateInput(format="%Y-%m-%d"),
            CustomTimeInput(format="%H:%M"),
        )
        super().__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        if value:
            value = to_current_timezone(value)
            return [value.date(), value.time()]
        return [None, None]
