from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, ListView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from dynamic_preferences.forms import preference_form_builder

from ephios.core.forms.events import EventTypeForm, EventTypePreferenceForm
from ephios.core.models import EventType
from ephios.extra.mixins import CustomPermissionRequiredMixin


class EventTypeUpdateView(CustomPermissionRequiredMixin, TemplateView, SingleObjectMixin):
    template_name = "core/eventtype_form.html"
    permission_required = "core.change_eventtype"
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

        if all([form.is_valid(), preference_form.is_valid()]):
            event_type = form.save()
            preference_form.update_preferences()
            messages.success(
                self.request, _("The event type {type} has been saved.").format(type=event_type)
            )
            return redirect(reverse("core:settings_eventtype_list"))

        return self.render_to_response(
            self.get_context_data(form=form, preference_form=preference_form)
        )


class EventTypeListView(CustomPermissionRequiredMixin, ListView):
    permission_required = "core.view_eventtype"
    accept_object_perms = False
    model = EventType


class EventTypeDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "core.delete_eventtype"
    model = EventType

    def get_success_url(self):
        messages.info(
            self.request, _("Eventtype {type} succesfully deleted.").format(type=self.object)
        )
        return reverse("core:settings_eventtype_list")


class EventTypeCreateView(CustomPermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "core.add_eventtype"
    accept_object_perms = False
    template_name = "core/eventtype_form.html"
    model = EventType
    fields = ["title"]
    success_message = _(
        "Event type was created. More settings for this event type can be managed below."
    )

    def get_success_url(self):
        return reverse("core:settings_eventtype_edit", kwargs={"pk": self.object.pk})
