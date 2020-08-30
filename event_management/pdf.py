from django.views.generic.detail import SingleObjectMixin
from django_renderpdf.views import PDFView

from event_management.models import Event


class EventPDFView(SingleObjectMixin, PDFView):
    template_name = "event_management/event_detail.html"
    model = Event

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        context["request"] = self.request
        context["without_controls"] = True
        return context
