from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.generic import (
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)
from guardian.shortcuts import get_objects_for_user

from event_management.forms import EventForm, ShiftFormSet
from event_management.models import (
    Event,
    Shift,
)


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "event_management/home.html"


class EventListView(LoginRequiredMixin, ListView):
    model = Event

    def get_queryset(self):
        return get_objects_for_user(self.request.user, "event_management.view_event")


class EventDetailView(PermissionRequiredMixin, DetailView):
    model = Event
    permission_required = "event_management.view_event"


class EventUpdateView(PermissionRequiredMixin, UpdateView):
    model = Event
    permission_required = "event_management.change_event"


class EventCreateView(PermissionRequiredMixin, View):
    template_name = "event_management/event_form.html"
    permission_required = "event_management.add_event"

    def get(self, request, *args, **kwargs):
        event_form = EventForm(initial={"responsible_persons": request.user})
        event_form.fields["visible_for"].queryset = get_objects_for_user(
            request.user, "publish_event_for_group", klass=Group
        )
        shift_formset = ShiftFormSet(queryset=Shift.objects.none())
        return render(
            request, self.template_name, {"event_form": event_form, "shift_formset": shift_formset}
        )

    def post(self, request, *args, **kwargs):
        event_form = EventForm(request.POST)
        event_form.fields["visible_for"].queryset = get_objects_for_user(
            request.user, "publish_event_for_group", klass=Group
        )
        shift_formset = ShiftFormSet(request.POST)
        if event_form.is_valid() and shift_formset.is_valid():
            event = event_form.save()
            shifts = shift_formset.save(commit=False)
            for shift in shifts:
                shift.event = event
                shift.signup_method_slug = "instant_confirmation"
                shift.signup_configuration = ""
                shift.save()
            return HttpResponseRedirect(event.get_absolute_url())
        return render(
            request, self.template_name, {"event_form": event_form, "shift_formset": shift_formset}
        )


class EventDeleteView(PermissionRequiredMixin, DeleteView):
    model = Event
    permission_required = "event_management.delete_event"


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
