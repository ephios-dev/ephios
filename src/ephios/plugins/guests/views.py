from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Prefetch
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.models import AbstractParticipation, Event
from ephios.core.views.signup import BaseShiftActionView
from ephios.extra.auth import access_exempt
from ephios.extra.widgets import CustomDateInput
from ephios.plugins.guests.models import EventGuestShare, GuestUser
from ephios.plugins.guests.notifications import GuestUserSignupNotification


@access_exempt
class RedirectAuthenticatedUserMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_authenticated_url())
        if "ephios.plugins.guests" not in global_preferences_registry.manager().get(
            "general__enabled_plugins"
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_authenticated_url(self):
        return reverse("core:home")


@access_exempt
class GuestRegistrationView(RedirectAuthenticatedUserMixin, CreateView):
    model = GuestUser
    form_class = forms.modelform_factory(
        GuestUser,
        fields=["email", "display_name", "date_of_birth", "phone", "qualifications"],
        widgets={
            "qualifications": Select2MultipleWidget,
            "date_of_birth": CustomDateInput,
        },
    )

    def get_event(self):
        try:
            return Event.all_objects.get(pk=self.kwargs.get("event_id"))
        except Event.DoesNotExist as e:
            raise PermissionDenied() from e

    def get_authenticated_url(self):
        messages.info(self.request, _("Log out to register as guest."))
        return self.get_event().get_absolute_url()

    def get_context_data(self, **kwargs):
        kwargs.setdefault("event", self.event)
        return super().get_context_data(**kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.event = self.get_event()
        input_token = kwargs["public_signup_token"]
        try:
            EventGuestShare.objects.get(event=self.event, active=True, token=input_token)
        except EventGuestShare.DoesNotExist as e:
            raise PermissionDenied from e
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.event = self.event
        try:
            guest = form.save()
        except IntegrityError:
            # unique_together constraint not passed
            form.add_error(
                None,
                _(
                    "You already registered as a guest for this event. We sent you an email with a link that you can use to change your participation."
                ),
            )
            guest = GuestUser.objects.get(email=form.cleaned_data["email"], event=self.event)
            GuestUserSignupNotification.send(
                event_title=self.event.title,
                guest_name=guest.display_name,
                email=guest.email,
                event_url=guest.as_participant().reverse_event_detail(self.event),
            )
            return self.form_invalid(form)
        event_url = guest.as_participant().reverse_event_detail(self.event)
        GuestUserSignupNotification.send(
            event_title=self.event.title,
            guest_name=guest.display_name,
            email=guest.email,
            event_url=event_url,
        )
        messages.info(self.request, _("Save the URL of this page to access this site later."))
        return redirect(event_url)


class GuestEventDetailView(RedirectAuthenticatedUserMixin, DetailView):
    model = GuestUser
    template_name = "guests/event_detail.html"

    def get_authenticated_url(self):
        messages.info(self.request, _("Log out to view the guest version of this page."))
        return self.get_object().event.get_absolute_url()

    def get_event(self):
        return (
            Event.objects
            .filter(id=self.get_object().event_id)
            .prefetch_related(
                Prefetch(
                    "shifts__participations",
                    queryset=AbstractParticipation.objects.all().with_show_participant_data_to(
                        participant=self.get_object().as_participant()
                    ),
                )
            )
            .first()
        )

    def get_context_data(self, **kwargs):
        kwargs["event"] = self.get_event()
        return super().get_context_data(**kwargs)

    def get_object(self, queryset=None):
        try:
            return GuestUser.objects.get(access_token=self.kwargs.get("guest_access_token"))
        except GuestUser.DoesNotExist as e:
            raise PermissionDenied from e


class GuestUserShiftActionView(RedirectAuthenticatedUserMixin, BaseShiftActionView):
    def get_participant(self):
        try:
            return GuestUser.objects.get(
                access_token=self.kwargs.get("guest_access_token")
            ).as_participant()
        except GuestUser.DoesNotExist as e:
            raise PermissionDenied from e
