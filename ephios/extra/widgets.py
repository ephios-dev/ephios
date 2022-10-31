from django.forms import DateInput, MultiWidget, TimeInput
from django.forms.utils import to_current_timezone
from django.forms.widgets import Input


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


class ColorInput(Input):
    input_type = "color"
