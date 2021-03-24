import typing

from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import FormView
from dynamic_preferences.forms import global_preference_form_builder

from ephios.core.signals import administration_settings_section
from ephios.extra.mixins import StaffRequiredMixin


def get_available_administration_settings_sections(request):
    sections = [
        {
            "label": _("General"),
            "url": reverse("core:settings_general"),
            "active": request.resolver_match.url_name == "settings_general",
        },
        {
            "label": _("Event types"),
            "url": reverse("core:settings_eventtype_list"),
            "active": request.resolver_match.url_name.startswith("settings_eventtype"),
        },
    ]
    for __, result in administration_settings_section.send(None, request=request):
        sections += result
    return sections


class SettingsViewMixin(FormView if typing.TYPE_CHECKING else object):
    def get_context_data(self, **kwargs):
        kwargs["settings_sections"] = get_available_administration_settings_sections(self.request)
        return super().get_context_data(**kwargs)


class GeneralSettingsView(StaffRequiredMixin, SuccessMessageMixin, SettingsViewMixin, FormView):
    template_name = "core/settings/general.html"
    success_message = _("Settings saved successfully.")

    def get_form_class(self):
        return global_preference_form_builder(section="general")

    def form_valid(self, form):
        form.update_preferences()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("core:settings_general")
