from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, ListView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from dynamic_preferences.forms import preference_form_builder

from ephios.extra.permissions import CustomPermissionRequiredMixin
from ephios.user_management.forms.events import EventTypeForm, EventTypePreferenceForm
from ephios.user_management.models import EventType


class EventTypeUpdateView(CustomPermissionRequiredMixin, TemplateView, SingleObjectMixin):
    template_name = "user_management/eventtype_form.html"
    permission_required = "user_management.add_event"
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
            return redirect(reverse("user_management:settings_eventtype_list"))

        return self.render_to_response(
            self.get_context_data(form=form, preference_form=preference_form)
        )


class EventTypeListView(CustomPermissionRequiredMixin, ListView):
    permission_required = "user_management.add_event"
    model = EventType


class EventTypeDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "user_management.add_event"
    model = EventType

    def get_success_url(self):
        messages.info(
            self.request, _("Eventtype {type} succesfully deleted.").format(type=self.object)
        )
        return reverse("user_management:settings_eventtype_list")


class EventTypeCreateView(CustomPermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "user_management.add_event"
    template_name = "event_management/../templates/user_management/eventtype_form.html"
    model = EventType
    fields = ["title", "can_grant_qualification"]
    success_message = _(
        "Eventtype succesfully created. More settings for this eventtype can be managed below. "
    )

    def get_success_url(self):
        return reverse("user_management:setting_eventtype_edit", kwargs=dict(pk=self.object.pk))
