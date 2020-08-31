from django.forms import DateInput, TimeInput, SplitDateTimeWidget, MultiWidget
from django.forms.utils import to_current_timezone


class CustomDateInput(DateInput):
    template_name = "event_management/fragments/custom_date_input.html"


class CustomTimeInput(TimeInput):
    template_name = "event_management/fragments/custom_time_input.html"


class CustomSplitDateTimeInput(SplitDateTimeWidget):
    pass


class CustomSplitDateTimeWidget(MultiWidget):
    """
    A widget that splits datetime input into two <input type="text"> boxes.
    """

    supports_microseconds = False
    # template_name = "django/forms/widgets/splitdatetime.html"

    def __init__(self):
        widgets = (
            CustomDateInput(),
            CustomTimeInput(),
        )
        super().__init__(widgets)

    def decompress(self, value):
        if value:
            value = to_current_timezone(value)
            return [value.date(), value.time()]
        return [None, None]
