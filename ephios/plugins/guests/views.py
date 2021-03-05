from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView

from ephios.core.models import Event
from ephios.core.views.signup import BaseShiftActionView
from ephios.plugins.guests.models import GuestUser


class GuestRegistrationView(CreateView):
    model = GuestUser
    fields = ["email", "first_name", "last_name", "date_of_birth", "phone", "qualifications"]

    def get_context_data(self, **kwargs):
        kwargs.setdefault("event", self.event)
        return super().get_context_data(**kwargs)

    def dispatch(self, request, *args, **kwargs):
        try:
            self.event = Event.objects.get(pk=self.kwargs.get("event_id"))
        except Event.DoesNotExist:
            raise PermissionDenied()
        token = kwargs["public_signup_token"]
        # todo check token for event.
        if token != "secret":
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        guest = form.save(commit=False)
        guest.event = self.event
        guest.save()
        return redirect(guest.as_participant().reverse_event_detail(self.event))


class GuestEventDetailView(DetailView):
    model = GuestUser
    template_name = "core/event_detail.html"

    def get_context_data(self, **kwargs):
        kwargs["event"] = self.get_object().event
        return super().get_context_data(**kwargs)

    def get_object(self, queryset=None):
        try:
            return GuestUser.objects.get(access_token=self.kwargs.get("guest_access_token"))
        except GuestUser.DoesNotExist:
            raise PermissionDenied()


class GuestUserShiftActionView(BaseShiftActionView):
    def get_participant(self):
        try:
            return GuestUser.objects.get(
                access_token=self.kwargs.get("guest_access_token")
            ).as_participant()
        except GuestUser.DoesNotExist:
            raise PermissionDenied()
