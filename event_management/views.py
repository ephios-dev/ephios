from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import (
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from event_management.models import (
    Event,
    Shift,
)


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "event_management/home.html"


class EventListView(LoginRequiredMixin, ListView):
    model = Event


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event


class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event


# TODO rename to signup
class ShiftRegisterView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        shift = get_object_or_404(Shift, id=self.kwargs["pk"])
        return shift.signup_method.signup_view(request, *args, **kwargs)


"""
    def get_redirect_url(self, *args, **kwargs):
        shift = get_object_or_404(Shift, id=self.kwargs["pk"])
        if self.request.user.is_minor and not shift.minors_allowed:
            messages.error(
                request=self.request, message="Minors are not allowed for this shift."
            )
        else:
            try:
                LocalParticipation(user=self.request.user, shift=shift).save()
                messages.success(
                    request=self.request,
                    message="Successfully registered for shift on {}".format(
                        shift.start_time
                    ),
                )
            except IntegrityError as e:
                messages.error(
                    request=self.request,
                    message="You already registered for this shift.",
                )
        return reverse(
            "event_management:event_detail", kwargs={"pk": shift.event.id}
        )
        """
