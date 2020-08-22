from django.forms import DateInput, TimeInput


class CustomDateInput(DateInput):
    template_name = "event_management/custom_date_input.html"


class CustomTimeInput(TimeInput):
    template_name = "event_management/custom_time_input.html"
