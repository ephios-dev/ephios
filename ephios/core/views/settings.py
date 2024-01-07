from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import FormView, TemplateView
from django.views.generic.edit import UpdateView
from dynamic_preferences.forms import global_preference_form_builder

from ephios.core.forms.users import UserNotificationPreferenceForm, UserOwnDataForm
from ephios.core.services.health.healthchecks import run_healthchecks
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
        sections.append(
            {
                "label": _("App integrations"),
                "url": reverse("api:settings-oauth-app-list"),
                "active": "settings-oauth" in request.resolver_match.url_name,
            }
        )
        sections.append(
            {
                "label": _("Identity providers"),
                "url": reverse("core:settings_idp_list"),
                "active": "settings_idp" in request.resolver_match.url_name,
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


class InstanceSettingsView(StaffRequiredMixin, SuccessMessageMixin, FormView):
    template_name = "core/settings/settings_instance.html"
    success_message = _("Settings saved successfully.")

    def get_form_class(self):
        return global_preference_form_builder(section="general")

    def form_valid(self, form):
        form.update_preferences()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("core:settings_instance")

    def get_context_data(self, **kwargs):
        if self.request.user.is_superuser:
            kwargs["healthchecks"] = list(run_healthchecks())
        return super().get_context_data(**kwargs)


class PersonalDataSettingsView(LoginRequiredMixin, UpdateView):
    template_name = "core/settings/settings_personal_data.html"
    form_class = UserOwnDataForm
    success_url = reverse_lazy("core:settings_personal_data")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, form.cleaned_data["preferred_language"])
        return response


class CalendarSettingsView(LoginRequiredMixin, TemplateView):
    template_name = "core/settings/settings_calendar.html"

    def get_context_data(self, **kwargs):
        kwargs["userprofile"] = self.request.user
        return super().get_context_data(**kwargs)


class NotificationSettingsView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    template_name = "core/settings/settings_notifications.html"
    success_message = _("Settings succesfully saved.")

    def get_form(self, form_class=None):
        return UserNotificationPreferenceForm(self.request.POST or None, user=self.request.user)

    def get_success_url(self):
        return reverse("core:settings_notifications")

    def form_valid(self, form):
        form.save_preferences()
        return super().form_valid(form)


class PasswordChangeSettingsView(SuccessMessageMixin, PasswordChangeView):
    template_name = "core/settings/password_change_form.html"
    success_url = reverse_lazy("core:home")
    success_message = _("Password changed successfully.")
