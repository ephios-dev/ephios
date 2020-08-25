from django.forms import DateInput, TimeInput


class CustomDateInput(DateInput):
    template_name = "event_management/fragments/custom_date_input.html"


class CustomTimeInput(TimeInput):
    template_name = "event_management/fragments/custom_time_input.html"
