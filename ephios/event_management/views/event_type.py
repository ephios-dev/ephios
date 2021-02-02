from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from django.views.generic.detail import SingleObjectMixin
from dynamic_preferences.forms import preference_form_builder

from ephios.event_management.forms import EventTypeForm, EventTypePreferenceForm
from ephios.event_management.models import EventType
from ephios.extra.permissions import CustomPermissionRequiredMixin


class EventTypeUpdateView(CustomPermissionRequiredMixin, TemplateView, SingleObjectMixin):
    template_name = "event_management/event_type_form.html"
    permission_required = "event_management.add_event"
    model = EventType

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_preference_form(self):
        form_class = preference_form_builder(EventTypePreferenceForm, instance=self.object)
        return form_class(self.request.POST or None)

    def get_context_data(self, **kwargs):
        kwargs.setdefault("form", EventTypeForm(self.request.POST or None, instance=self.object))
        kwargs.setdefault("preference_form", self.get_preference_form())
        return super().get_context_data(**kwargs)

    def post(self, *args, **kwargs):
        form = EventTypeForm(self.request.POST or None, instance=self.object)
        preference_form = self.get_preference_form()

        if form.is_valid() and preference_form.is_valid():
            event_type = form.save()
            preference_form.update_preferences()
            messages.success(
                self.request, _("The event type {type} has been saved.").format(type=event_type)
            )
            return redirect(reverse("event_management:index"))

        return self.render_to_response(
            self.get_context_data(form=form, preference_form=preference_form)
        )
