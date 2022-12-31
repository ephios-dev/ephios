import json
from calendar import _nextmonth, _prevmonth
from datetime import datetime, time, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import BooleanField, Case, Max, Min, Prefetch, Q, QuerySet, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
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

from ephios.core.calendar import ShiftCalendar
from ephios.core.forms.events import EventDuplicationForm, EventForm, EventNotificationForm
from ephios.core.models import Event, EventType, Shift
from ephios.core.services.notifications.types import (
    CustomEventParticipantNotification,
    EventReminderNotification,
    NewEventNotification,
)
from ephios.core.signals import event_forms
from ephios.extra.mixins import (
    CanonicalSlugDetailMixin,
    CustomPermissionRequiredMixin,
    PluginFormMixin,
)
from ephios.extra.permissions import get_groups_with_perms
from ephios.extra.widgets import CustomDateInput


class EventFilterForm(forms.Form):
    query = forms.CharField(
        label=_("Search for…"),
        widget=forms.TextInput(attrs={"placeholder": _("Search for…"), "autofocus": "autofocus"}),
        required=False,
    )
    event_types = forms.ModelMultipleChoiceField(
        queryset=EventType.objects.all(),
        label=EventType._meta.verbose_name,
        required=False,
    )
    date_mode = forms.ChoiceField(
        label=_("Date mode"),
        required=False,
        choices=[
            ("until", _("until")),
            ("from", _("from")),
        ],
        initial="from",
    )
    date = forms.DateField(
        label=_("Date"),
        required=False,
        widget=CustomDateInput,
    )
    participation_states = forms.ChoiceField(
        label=_("Participation"),
        required=False,
        choices=[  # events only have aggregated participation state, so we pick some useful ones
            ("all", _("all")),
            ("none", _("no response")),
            ("confirmed", _("confirmed")),
            ("requested-confirmed", _("requested or confirmed")),
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.now().date()

    def clean_date(self):
        if not self.cleaned_data["date"]:
            return timezone.now().date()
        return self.cleaned_data["date"]

    def filter_events(self, qs: QuerySet[Event]):
        data = self.cleaned_data

        date = self.cleaned_data["date"]
        if self.cleaned_data.get("date_mode", "from") == "from":
            qs = qs.filter(end_time__gte=datetime.combine(date, time.min))
            qs.order_by("start_time", "end_time")
        else:  # until
            qs = qs.filter(start_time__lte=datetime.combine(date, time.max))
            qs.order_by("-start_time", "-end_time")  # TODO doesn't seem to work?!

        if event_types := self.cleaned_data.get("event_types"):
            qs = qs.filter(type__in=event_types)

        if query := self.cleaned_data.get("query"):
            qs.filter(
                Q(title__icontains=query)
                | Q(location__icontains=query)
                | Q(description__icontains=query)
            )

        # TODO participation state filter
        return qs

    def filter_shifts(self, qs: QuerySet[Shift]):
        data = self.cleaned_data
        # TODO do filtering
        return qs

    def get_calendar_month(self):
        "Return, even if the form is invalid, a tuple of year, month for the calendar to show"
        if self.is_valid() and (date := self.cleaned_data.get("date")):
            return date.year, date.month
        now = timezone.now()
        return now.year, now.month


class EventListView(LoginRequiredMixin, ListView):
    model = Event

    @property
    def template_name(self):
        mode = self.request.session.get("event_list_view_mode", "list")
        # don't want to put the mode in the filename as the value in the session might be invalid
        if mode == "calendar":
            return "core/event_calendar.html"
        return "core/event_list.html"

    def get_queryset(self):
        qs = (
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
            .select_related("type")
            .prefetch_related("shifts")
            .prefetch_related(Prefetch("shifts__participations"))
        )
        if self.filter_form.is_valid():
            qs = self.filter_form.filter_events(qs)
        else:
            # saveguard for not loading too many events
            qs = qs.filter(end_time__gte=timezone.now()).order_by("start_time")
        return qs

    @cached_property
    def filter_form(self):
        return EventFilterForm(data=self.request.GET or None)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["eventtypes"] = EventType.objects.all()
        ctx["filter_form"] = self.filter_form

        if (new_mode := self.request.GET.get("mode")) in {"list", "calendar"}:
            self.request.session["event_list_view_mode"] = new_mode
        mode = self.request.session.get("event_list_view_mode", "list")
        ctx["mode"] = mode

        if mode == "calendar":
            ctx.update(self._get_calendar_context())
        return ctx

    def _get_calendar_context(self):
        shifts = Shift.objects.filter(
            event__in=get_objects_for_user(self.request.user, "core.view_event", klass=Event),
        )
        year, month = self.filter_form.get_calendar_month()
        shifts = shifts.filter(start_time__year=year, start_time__month=month)
        if self.filter_form.is_valid():
            shifts = self.filter_form.filter_shifts(shifts)
        calendar = ShiftCalendar(shifts)

        prevyear, prevmonth = _prevmonth(year, month)
        nextyear, nextmonth = _nextmonth(year, month)
        return {
            "calendar": mark_safe(calendar.formatmonth(year, month)),
            "prev_month_first": datetime.min.replace(year=prevyear, month=prevmonth),
            "next_month_first": datetime.min.replace(year=nextyear, month=nextmonth),
        }


class EventDetailView(CustomPermissionRequiredMixin, CanonicalSlugDetailMixin, DetailView):
    model = Event
    permission_required = "core.view_event"

    def get_queryset(self):
        base = Event.objects.all()
        if self.request.user.has_perm("core.add_event"):
            base = Event.all_objects.all()
        return base.prefetch_related("shifts", "shifts__participations")


class EventUpdateView(CustomPermissionRequiredMixin, PluginFormMixin, UpdateView):
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

    def get_plugin_forms(self):
        return event_forms.send(sender=None, event=self.object, request=self.request)


class EventCreateView(CustomPermissionRequiredMixin, PluginFormMixin, CreateView):
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

    def get_plugin_forms(self):
        return event_forms.send(sender=None, event=self.object, request=self.request)


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
            datetime.now() + timedelta(days=7305),  # allow dates up to twenty years in the future
            inc=True,
            dtstart=datetime.combine(
                forms.DateField().to_python(self.request.POST["start_date"]), datetime.min.time()
            ),
        )
        for date in occurrences:
            event = self.get_object()
            start_date = event.get_start_time().date()
            shifts = list(event.shifts.all())
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
                        + timedelta(days=7305),  # allow dates up to twenty years in the future
                        inc=True,
                        dtstart=datetime.combine(
                            forms.DateField().to_python(self.request.POST["dtstart"]),
                            datetime.min.time(),
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

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "event": self.object}

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
