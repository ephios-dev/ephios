import json

import guardian.mixins
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.timezone import get_default_timezone
from django.views.generic import (
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
    CreateView,
    RedirectView,
)
from django.views.generic.detail import SingleObjectMixin
from guardian.shortcuts import get_objects_for_user, get_users_with_perms

from event_management import mail
from event_management.forms import EventForm, ShiftForm
from event_management.models import (
    Event,
    Shift,
    AbstractParticipation,
)
from django.utils.translation import gettext as _

from event_management.signup import SignupError, DeclineError
from jep.permissions import get_groups_with_perms


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "event_management/home.html"


class EventListView(LoginRequiredMixin, ListView):
    model = Event

    def get_queryset(self):
        return get_objects_for_user(self.request.user, "event_management.view_event")


class EventDetailView(guardian.mixins.PermissionRequiredMixin, DetailView):
    model = Event
    permission_required = "event_management.view_event"

    def get_queryset(self):
        if self.request.user.has_perm("event_management.add_event"):
            return Event.all_objects
        else:
            return Event.objects


class EventUpdateView(guardian.mixins.PermissionRequiredMixin, UpdateView):
    model = Event
    queryset = Event.all_objects
    permission_required = "event_management.change_event"
    raise_exception = True
    accept_global_perms = True

    def get_form(self, form_class=None):
        visible_queryset = get_objects_for_user(
            self.request.user, "publish_event_for_group", klass=Group
        )
        initial = {
            "visible_for": get_groups_with_perms(self.object, only_with_perms_in=["view_event"]),
            "responsible_persons": get_users_with_perms(
                self.object, only_with_perms_in=["change_event"], with_group_users=False
            ),
            "responsible_groups": get_groups_with_perms(
                self.object, only_with_perms_in=["change_event"]
            ),
        }
        event_form = EventForm(self.request.POST or None, instance=self.object, initial=initial)
        event_form.fields["visible_for"].queryset = visible_queryset
        return event_form


class EventCreateView(PermissionRequiredMixin, CreateView):
    template_name = "event_management/event_form.html"
    permission_required = "event_management.add_event"

    def get_form(self, form_class=None):
        visible_for_queryset = get_objects_for_user(
            self.request.user, "publish_event_for_group", klass=Group
        )
        event_form = EventForm(
            self.request.POST or None,
            initial={
                "responsible_persons": get_user_model().objects.filter(pk=self.request.user.pk),
                "responsible_groups": Group.objects.none(),
                "visible_for": visible_for_queryset,
            },
        )
        event_form.fields["visible_for"].queryset = visible_for_queryset
        return event_form

    def get_context_data(self, **kwargs):
        inactive_events = Event.all_objects.filter(active=False)
        kwargs.setdefault("inactive_events", inactive_events)
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse("event_management:event_createshift", kwargs={"pk": self.object.pk})


class EventActivateView(PermissionRequiredMixin, RedirectView):
    permission_required = "event_management.add_event"

    def get_redirect_url(self, *args, **kwargs):
        event = get_object_or_404(Event.all_objects, pk=kwargs["pk"])
        if not event.active:
            event.active = True
            event.save()
            messages.success(
                self.request, _("The event {title} has been saved.".format(title=event.title))
            )
            mail.new_event(event)
        return event.get_absolute_url()


class EventDeleteView(PermissionRequiredMixin, DeleteView):
    queryset = Event.all_objects
    permission_required = "event_management.delete_event"
    success_url = reverse_lazy("event_management:event_list")


class ShiftCreateView(PermissionRequiredMixin, TemplateView):
    permission_required = "event_management.add_event"
    template_name = "event_management/shift_form.html"

    def get_event(self):
        return get_object_or_404(Event.all_objects, pk=self.kwargs.get("pk"))

    def get_shift_form(self):
        return ShiftForm(self.request.POST or None)

    def get_context_data(self, **kwargs):
        event = self.get_event()
        kwargs.setdefault("event", event)
        kwargs.setdefault("form", self.get_shift_form())
        return super().get_context_data(**kwargs)

    def post(self, *args, **kwargs):
        form = self.get_shift_form()
        try:
            from event_management.signup import signup_method_from_slug

            signup_method = signup_method_from_slug(self.request.POST["signup_method_slug"])
            configuration_form = signup_method.get_configuration_form(self.request.POST)
        except ValueError as e:
            raise ValidationError(e)
        if form.is_valid() and configuration_form.is_valid():
            shift = form.save(commit=False)
            event = self.get_event()
            shift.event = event
            shift.signup_configuration = configuration_form.get_configuration()
            shift.save()
            if "addAnother" in self.request.POST:
                return redirect(
                    reverse(
                        "event_management:event_createshift", kwargs={"pk": self.kwargs.get("pk")}
                    )
                )
            else:
                event.active = True
                event.save()
                messages.success(
                    self.request, _("The event {title} has been saved.".format(title=event.title))
                )
                return redirect(event.get_absolute_url())
        else:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    configuration_form=signup_method.render_configuration_form(configuration_form),
                )
            )


class ShiftConfigurationFormView(View):
    def get(self, request, *args, **kwargs):
        from event_management.signup import signup_method_from_slug

        signup_method = signup_method_from_slug(self.kwargs.get("slug"))
        return HttpResponse(signup_method.render_configuration_form())


class ShiftUpdateView(guardian.mixins.PermissionRequiredMixin, TemplateView, SingleObjectMixin):
    model = Shift
    template_name = "event_management/shift_form.html"
    permission_required = "event_management.change_event"
    raise_exception = True
    accept_global_perms = True

    def get_permission_object(self):
        return self.get_object().event

    def get_shift_form(self):
        return ShiftForm(
            self.request.POST or None,
            instance=self.object,
            initial={
                "date": self.object.meeting_time.date(),
                "meeting_time": self.object.meeting_time.astimezone(get_default_timezone()).time(),
                "start_time": self.object.start_time.astimezone(get_default_timezone()).time(),
                "end_time": self.object.end_time.astimezone(get_default_timezone()).time(),
            },
        )

    def get_configuration_form(self):
        return self.object.signup_method.render_configuration_form(
            data=self.request.POST or None, initial=json.loads(self.object.signup_configuration)
        )

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        kwargs.setdefault("event", self.object.event)
        kwargs.setdefault("form", self.get_shift_form())
        kwargs.setdefault("configuration_form", self.get_configuration_form())
        return super().get_context_data(**kwargs)

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_shift_form()
        try:
            from event_management.signup import signup_method_from_slug

            signup_method = signup_method_from_slug(self.request.POST["signup_method_slug"])
            configuration_form = signup_method.get_configuration_form(self.request.POST)
        except ValueError as e:
            raise ValidationError(e)
        if form.is_valid() and configuration_form.is_valid():
            shift = form.save(commit=False)
            shift.signup_configuration = configuration_form.get_configuration()
            shift.save()
            if "addAnother" in self.request.POST:
                return redirect(
                    reverse("event_management:event_createshift", kwargs={"pk": shift.event.pk})
                )
            else:
                messages.success(
                    self.request, _("The shift {shift} has been saved.".format(shift=shift))
                )
                return redirect(self.object.event.get_absolute_url())
        else:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    configuration_form=signup_method.render_configuration_form(configuration_form),
                )
            )


class ShiftDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "event_management.change_event"
    model = Shift

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.event.shifts.count() == 1:
            messages.error(self.request, _("You cannot delete the last shift!"))
            return redirect(self.object.event.get_absolute_url())
        else:
            return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        messages.success(self.request, _("The shift has been deleted."))
        return self.object.event.get_absolute_url()


# TODO rename to signup
class ShiftRegisterView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        shift = get_object_or_404(Shift, id=self.kwargs["pk"])
        return shift.signup_method.signup_view(request, *args, **kwargs)


class ShiftDeclineView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        shift = get_object_or_404(Shift, id=self.kwargs["pk"])
        return shift.signup_method.decline_view(self.request)
