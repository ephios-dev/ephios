from collections import defaultdict
from urllib.parse import urljoin

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from django.views.generic import FormView
from django.views.generic.edit import UpdateView
from dynamic_preferences.forms import global_preference_form_builder

from ephios.core.dynamic import dynamic_settings
from ephios.core.forms.users import UserNotificationPreferenceForm, UserOwnDataForm
from ephios.core.models.users import IdentityProvider
from ephios.core.services.health.healthchecks import run_healthchecks
from ephios.core.signals import settings_sections
from ephios.core.views.auth import show_login_form
from ephios.extra.mixins import StaffRequiredMixin

SETTINGS_PERSONAL_SECTION_KEY = _("Personal")
SETTINGS_MANAGEMENT_SECTION_KEY = _("Management")


def get_available_settings_sections(request):
    sections = defaultdict(list)
    sections[SETTINGS_PERSONAL_SECTION_KEY] += [
        {
            "label": _("Personal data"),
            "url": reverse("core:settings_personal_data"),
            "active": request.resolver_match.url_name == "settings_personal_data",
        },
        {
            "label": _("Notifications"),
            "url": reverse("core:settings_notifications"),
            "active": request.resolver_match.url_name == "settings_notifications",
        },
        {
            "label": _("Calendar"),
            "url": reverse("core:settings_calendar"),
            "active": request.resolver_match.url_name == "settings_calendar",
        },
        {
            "label": _("Integrations"),
            "url": reverse("api:settings-access-token-list"),
            "active": "settings-access-token" in request.resolver_match.url_name,
        },
    ]
    if show_login_form(request, IdentityProvider.objects.all()):
        sections[SETTINGS_PERSONAL_SECTION_KEY].append({
            "label": _("Change password"),
            "url": reverse("core:settings_password_change"),
            "active": request.resolver_match.url_name == "settings_password_change",
        })
    if request.user.is_staff:
        sections[SETTINGS_MANAGEMENT_SECTION_KEY].append({
            "label": pgettext_lazy("Settings section name", "General"),
            "url": reverse("core:settings_instance"),
            "active": request.resolver_match.url_name == "settings_instance",
        })
        sections[SETTINGS_MANAGEMENT_SECTION_KEY].append({
            "label": _("App integrations"),
            "url": reverse("api:settings-oauth-app-list"),
            "active": "settings-oauth" in request.resolver_match.url_name,
        })
        sections[SETTINGS_MANAGEMENT_SECTION_KEY].append({
            "label": _("Identity providers"),
            "url": reverse("core:settings_idp_list"),
            "active": "settings_idp" in request.resolver_match.url_name,
        })
    if request.user.has_perm("core.view_eventtype"):
        sections[SETTINGS_MANAGEMENT_SECTION_KEY].append({
            "label": _("Event types"),
            "url": reverse("core:settings_eventtype_list"),
            "active": request.resolver_match.url_name.startswith("settings_eventtype"),
        })

    for __, result in settings_sections.send(None, request=request):
        for item in result:
            group = item.pop("group")
            sections[group].append(item)
    return dict(sections)


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


class CalendarURLResetForm(forms.Form):
    reset = forms.BooleanField(required=True)


class CalendarSettingsView(LoginRequiredMixin, FormView):
    template_name = "core/settings/settings_calendar.html"
    success_message = _("Calendar-URL was reset.")
    success_url = reverse_lazy("core:settings_calendar")
    form_class = CalendarURLResetForm

    def get_context_data(self, **kwargs):
        kwargs["userprofile"] = self.request.user
        kwargs["calendar_url"] = self.get_calendar_url()
        return super().get_context_data(**kwargs)

    def get_calendar_url(self):
        location = reverse("core:user_event_feed", args=(self.request.user.calendar_token,))
        return urljoin(dynamic_settings.SITE_URL, location + "?requested=1&rejected=0")

    def form_valid(self, form):
        self.request.user.reset_calendar_token()
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


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
