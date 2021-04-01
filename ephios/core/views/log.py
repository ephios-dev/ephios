from django.views.generic import ListView

from ephios.extra.mixins import StaffRequiredMixin
from ephios.modellogging.models import LogEntry


class LogView(StaffRequiredMixin, ListView):
    template_name = "core/logentry_list.html"
    model = LogEntry
