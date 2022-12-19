import typing

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import FormView, TemplateView
from dynamic_preferences.forms import global_preference_form_builder

from ephios.core.forms.users import UserNotificationPreferenceForm
from ephios.core.signals import management_settings_sections
from ephios.extra.mixins import StaffRequiredMixin


def get_available_management_settings_sections(request):
    sections = []
    if request.user.is_staff:
        sections.append(
            {
                "label": _("ephios instance"),
                "url": reverse("core:settings_instance"),
                "active": request.resolver_match.url_name == "settings_instance",
            }
        )
    if request.user.has_perm("core.view_eventtype"):
        sections.append(
            {
                "label": _("Event types"),
                "url": reverse("core:settings_eventtype_list"),
                "active": request.resolver_match.url_name.startswith("settings_eventtype"),
            }
        )
    for __, result in management_settings_sections.send(None, request=request):
        sections += result
    return sections


class SettingsViewMixin(FormView if typing.TYPE_CHECKING else object):
    def get_context_data(self, **kwargs):
        kwargs["management_settings_sections"] = get_available_management_settings_sections(
            self.request
        )
        return super().get_context_data(**kwargs)


class InstanceSettingsView(StaffRequiredMixin, SuccessMessageMixin, SettingsViewMixin, FormView):
    template_name = "core/settings/settings_instance.html"
    success_message = _("Settings saved successfully.")

    def get_form_class(self):
        return global_preference_form_builder(section="general")

    def form_valid(self, form):
        form.update_preferences()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("core:settings_instance")


class PersonalDataSettingsView(LoginRequiredMixin, SettingsViewMixin, TemplateView):
    template_name = "core/settings/settings_personal_data.html"

    def get_context_data(self, **kwargs):
        kwargs["userprofile"] = self.request.user
        return super().get_context_data(**kwargs)


class CalendarSettingsView(LoginRequiredMixin, SettingsViewMixin, TemplateView):
    template_name = "core/settings/settings_calendar.html"

    def get_context_data(self, **kwargs):
        kwargs["userprofile"] = self.request.user
        return super().get_context_data(**kwargs)


class NotificationSettingsView(
    LoginRequiredMixin, SuccessMessageMixin, SettingsViewMixin, FormView
):
    template_name = "core/settings/settings_notifications.html"
    success_message = _("Settings succesfully saved.")

    def get_form(self, form_class=None):
        return UserNotificationPreferenceForm(self.request.POST or None, user=self.request.user)

    def get_success_url(self):
        return reverse("core:settings_notifications")

    def form_valid(self, form):
        form.update_preferences()
        return super().form_valid(form)


class PasswordChangeSettingsView(SuccessMessageMixin, SettingsViewMixin, PasswordChangeView):
    template_name = "core/settings/password_change_form.html"
    success_url = reverse_lazy("core:home")
    success_message = _("Password changed successfully.")
