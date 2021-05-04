import functools
import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import BooleanField, Case, Max, Min, Prefetch, When
from django.forms import DateField
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.timezone import get_current_timezone, make_aware
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)
from django.views.generic.detail import SingleObjectMixin
from guardian.shortcuts import assign_perm, get_objects_for_user, get_users_with_perms
from recurrence.forms import RecurrenceField

from ephios.core.forms.events import EventDuplicationForm, EventForm, EventNotificationForm
from ephios.core.models import Event, EventType, Shift
from ephios.core.services.notifications.types import (
    CustomEventParticipantNotification,
    EventReminderNotification,
    NewEventNotification,
)
from ephios.core.signals import event_forms
from ephios.extra.mixins import CanonicalSlugDetailMixin, CustomPermissionRequiredMixin
from ephios.extra.permissions import get_groups_with_perms


class EventListView(LoginRequiredMixin, ListView):
    model = Event

    def get_queryset(self):
        return (
            get_objects_for_user(self.request.user, "core.view_event")
            .annotate(
                start_time=Min("shifts__start_time"),
                end_time=Max("shifts__end_time"),
            )
            .annotate(
                can_change=Case(
                    When(
                        id__in=get_objects_for_user(self.request.user, ["core.change_event"]),
                        then=True,
                    ),
                    default=False,
                    output_field=BooleanField(),
                )
            )
            .filter(end_time__gte=timezone.now())
            .select_related("type")
            .prefetch_related("shifts")
            .prefetch_related(Prefetch("shifts__participations"))
            .order_by("start_time")
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        kwargs.setdefault("eventtypes", EventType.objects.all())
        return super().get_context_data(**kwargs)


class EventDetailView(CustomPermissionRequiredMixin, CanonicalSlugDetailMixin, DetailView):
    model = Event
    permission_required = "core.view_event"

    def get_queryset(self):
        if self.request.user.has_perm("core.add_event"):
            return Event.all_objects.all()
        return Event.objects.all()


class EventEditMixin:
    @functools.cached_property
    def plugin_forms(self):
        forms = []
        for __, resp in event_forms.send(sender=None, event=self.object, request=self.request):
            forms.extend(resp)
        return forms

    def get_context_data(self, **kwargs):
        kwargs["plugin_forms"] = self.plugin_forms
        return super().get_context_data(**kwargs)

    def is_valid(self, form):
        return form.is_valid() and all(plugin_form.is_valid() for plugin_form in self.plugin_forms)

    def form_valid(self, form):
        response = super().form_valid(form)
        for plugin_form in self.plugin_forms:
            plugin_form.save()
        return response


class EventUpdateView(CustomPermissionRequiredMixin, EventEditMixin, UpdateView):
    model = Event
    queryset = Event.all_objects.all()
    permission_required = "core.change_event"

    def get_form(self, form_class=None):
        return EventForm(
            data=self.request.POST or None, user=self.request.user, instance=self.object
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if self.is_valid(form):
            return self.form_valid(form)
        return self.form_invalid(form)


class EventCreateView(CustomPermissionRequiredMixin, EventEditMixin, CreateView):
    template_name = "core/event_form.html"
    permission_required = "core.add_event"
    accept_object_perms = False
    model = EventType

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self.object = form.instance
        if self.is_valid(form):
            return self.form_valid(form)
        return self.form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        self.eventtype = get_object_or_404(EventType, pk=self.kwargs.get("type"))
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        return EventForm(
            data=self.request.POST or None,
            user=self.request.user,
            eventtype=self.eventtype,
        )

    def get_context_data(self, **kwargs):
        inactive_events = Event.all_objects.filter(active=False)
        kwargs.setdefault("inactive_events", inactive_events)
        kwargs.setdefault("eventtype", self.eventtype)
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse("core:event_createshift", kwargs={"pk": self.object.pk})


class EventActivateView(CustomPermissionRequiredMixin, SingleObjectMixin, View):
    permission_required = "core.add_event"
    queryset = Event.all_objects.all()

    def post(self, request, *args, **kwargs):
        event = self.get_object()
        try:
            event.activate()
            messages.success(
                request,
                _("The event {title} has been saved.").format(title=event.title),
            )
        except ValidationError as e:
            messages.error(request, e)
        return redirect(event.get_absolute_url())


class EventDeleteView(CustomPermissionRequiredMixin, DeleteView):
    queryset = Event.all_objects.all()
    permission_required = "core.delete_event"
    success_url = reverse_lazy("core:event_list")


class EventArchiveView(CustomPermissionRequiredMixin, ListView):
    permission_required = "core.view_past_event"
    model = Event
    template_name = "core/event_archive.html"

    def get_queryset(self):
        return (
            get_objects_for_user(self.request.user, "core.view_event")
            .annotate(
                start_time=Min("shifts__start_time"),
                end_time=Max("shifts__end_time"),
            )
            .filter(end_time__lt=timezone.now())
            .select_related("type")
            .order_by("-start_time")
        )


class EventCopyView(CustomPermissionRequiredMixin, SingleObjectMixin, FormView):
    permission_required = "core.add_event"
    model = Event
    template_name = "core/event_copy.html"
    form_class = EventDuplicationForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = self.get_object()

    def form_valid(self, form):
        occurrences = form.cleaned_data["recurrence"].between(
            datetime.now() - timedelta(days=1),
            datetime.now() + timedelta(days=730),  # allow dates up to two years in the future
            inc=True,
            dtstart=datetime.combine(
                DateField().to_python(self.request.POST["start_date"]), datetime.min.time()
            ),
        )
        for date in occurrences:
            event = self.get_object()
            start_date = event.get_start_time().date()
            shifts = event.shifts.all()
            event.pk = None
            event.save()
            assign_perm(
                "view_event", get_groups_with_perms(self.get_object(), ["view_event"]), event
            )
            assign_perm(
                "change_event", get_groups_with_perms(self.get_object(), ["change_event"]), event
            )
            assign_perm(
                "change_event",
                get_users_with_perms(
                    self.get_object(), only_with_perms_in=["change_event"], with_group_users=False
                ),
                event,
            )

            shifts_to_create = []
            for shift in shifts:
                shift.pk = None
                # shifts on following days should have the same offset from the new date
                offset = shift.start_time.date() - start_date
                # shifts ending on the next day should end on the next day to the new date
                end_offset = shift.end_time.date() - shift.start_time.date()
                current_tz = get_current_timezone()
                shift.end_time = make_aware(
                    datetime.combine(
                        date.date() + offset + end_offset,
                        shift.end_time.astimezone(current_tz).time(),
                    )
                )
                shift.meeting_time = make_aware(
                    datetime.combine(
                        date.date() + offset, shift.meeting_time.astimezone(current_tz).time()
                    )
                )
                shift.start_time = make_aware(
                    datetime.combine(
                        date.date() + offset, shift.start_time.astimezone(current_tz).time()
                    )
                )
                shift.event = event
                shifts_to_create.append(shift)
            Shift.objects.bulk_create(shifts_to_create)

        messages.success(self.request, _("Event copied successfully."))
        return redirect(reverse("core:event_list"))


class RRuleOccurrenceView(CustomPermissionRequiredMixin, View):
    permission_required = "core.add_event"

    def post(self, *args, **kwargs):
        try:
            recurrence = RecurrenceField().clean(self.request.POST["recurrence_string"])
            return HttpResponse(
                json.dumps(
                    recurrence.between(
                        datetime.now() - timedelta(days=1),
                        datetime.now()
                        + timedelta(days=730),  # allow dates up to two years in the future
                        inc=True,
                        dtstart=datetime.combine(
                            DateField().to_python(self.request.POST["dtstart"]), datetime.min.time()
                        ),
                    ),
                    default=lambda obj: date_format(obj, format="SHORT_DATE_FORMAT"),
                )
            )
        except (TypeError, KeyError, ValidationError):
            return HttpResponse()


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "core/home.html"


class EventNotificationView(CustomPermissionRequiredMixin, SingleObjectMixin, FormView):
    model = Event
    permission_required = "core.change_event"
    template_name = "core/event_notification.html"
    form_class = EventNotificationForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = self.get_object()

    def form_valid(self, form):
        action = form.cleaned_data["action"]
        if action == form.NEW_EVENT:
            NewEventNotification.send(self.object)
        elif action == form.REMINDER:
            EventReminderNotification.send(self.object)
        elif action == form.PARTICIPANTS:
            CustomEventParticipantNotification.send(self.object, form.cleaned_data["mail_content"])
        messages.success(self.request, _("Notifications sent succesfully."))
        return redirect(self.object.get_absolute_url())
