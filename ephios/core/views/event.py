import json
from calendar import _nextmonth, _prevmonth
from collections import defaultdict
from datetime import datetime, time, timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import BooleanField, Case, Count, Max, Min, Prefetch, Q, QuerySet, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.timezone import get_current_timezone, make_aware
from django.utils.translation import gettext as _
from django.utils.translation import pgettext_lazy
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
from ephios.core.models import AbstractParticipation, Event, EventType, Shift
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
    types = forms.ModelMultipleChoiceField(
        label=_("event type"),
        queryset=EventType.objects.all(),
        required=False,
        widget=forms.SelectMultiple(
            attrs={"class": "flex-grow-1 h-0"}
        ),  # can't set it using crispy tag
    )
    direction = forms.ChoiceField(
        label=_("Date"),
        required=False,
        choices=[
            ("until", pgettext_lazy("event date filter", "until")),
            ("from", pgettext_lazy("event date filter", "from")),
        ],
        initial="from",
    )
    date = forms.DateField(
        label=_("Date"),
        required=False,
        widget=CustomDateInput,
    )
    state = forms.ChoiceField(
        label=_("State"),
        required=False,
        choices=[  # events only have aggregated participation state, so we pick some useful ones
            (None, _("all")),
            ("no-response", _("no response")),
            ("confirmed", _("confirmed")),
            ("requested-confirmed", _("requested or confirmed")),
            ("pending", _("disposition to do")),
        ],
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")

        # as a heuristic, save this to determine if the filter form was submitted through html
        self.was_submitted = False

        if (old_data := kwargs.get("data")) is not None:
            self.was_submitted = "direction" in old_data

            kwargs["data"] = MultiValueDict(
                old_data,
            )
            kwargs["data"]["date"] = old_data.get("date") or None
            kwargs["data"]["direction"] = old_data.get("direction") or "from"
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.now().date()

    def filter_events(self, qs: QuerySet[Event]):
        fdata = self.cleaned_data

        date = self.get_date()
        if fdata.get("direction", "from") == "from":
            qs = qs.filter(end_time__gte=make_aware(datetime.combine(date, time.min)))
            qs = qs.order_by("start_time", "end_time")
        else:  # until
            qs = qs.filter(start_time__lte=make_aware(datetime.combine(date, time.max)))
            qs = qs.order_by("-start_time", "-end_time")

        if event_types := fdata.get("types"):
            qs = qs.filter(type__in=event_types)

        if query := fdata.get("query"):
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(location__icontains=query)
                | Q(description__icontains=query)
            )

        if state_filter := fdata.get("state"):
            qs = {
                "confirmed": qs.filter(
                    **{f"state_{AbstractParticipation.States.CONFIRMED}_count__gt": 0}
                ),
                "requested-confirmed": qs.filter(
                    Q(**{f"state_{AbstractParticipation.States.CONFIRMED}_count__gt": 0})
                    | Q(**{f"state_{AbstractParticipation.States.REQUESTED}_count__gt": 0})
                ),
                "no-response": qs.filter(
                    **{f"state_{state}_count": 0 for state in AbstractParticipation.States}
                ),
                "pending": qs.filter(pending_disposition_count__gt=0),
            }.get(state_filter, qs)

        return qs

    def filter_shifts(self, qs: QuerySet[Shift]):
        """
        filter a shift queryset. Can't filter based on associated events, because we need
        more fine-grained filtering for participation states.
        """
        fdata = self.cleaned_data
        if event_types := fdata.get("types"):
            qs = qs.filter(event__type__in=event_types)

        if query := fdata.get("query"):
            qs = qs.filter(
                Q(event__title__icontains=query)
                | Q(event__location__icontains=query)
                | Q(event__description__icontains=query)
            )

        if state_filter := fdata.get("state"):
            qs = {
                "confirmed": qs.filter(
                    participations__localparticipation__user=self.request.user,
                    participations__state=AbstractParticipation.States.CONFIRMED,
                ).distinct(),
                "requested-confirmed": qs.filter(
                    participations__localparticipation__user=self.request.user,
                    participations__state__in=[
                        AbstractParticipation.States.CONFIRMED,
                        AbstractParticipation.States.REQUESTED,
                    ],
                ).distinct(),
                "no-response": qs.exclude(
                    participations__localparticipation__user=self.request.user,
                ).distinct(),
                "pending": qs.filter(
                    can_change=True, participations__state=AbstractParticipation.States.REQUESTED
                ).distinct(),
            }.get(state_filter, qs)

        return qs

    def get_date(self, default=None):
        "Return, even if the form is invalid, a date object for the calendar to show"
        if self.is_valid() and (date := self.cleaned_data.get("date")):
            return date
        return default or timezone.now().date()


class EventListView(LoginRequiredMixin, ListView):
    model = Event
    paginate_by = settings.DEFAULT_LISTVIEW_PAGINATION

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
            .annotate(
                pending_disposition_count=Count(
                    "shifts__participations",
                    filter=Q(
                        shifts__participations__state=AbstractParticipation.States.REQUESTED,
                        can_change=True,
                    ),
                ),
                **{
                    f"state_{state}_count": Count(
                        "shifts__participations",
                        filter=Q(
                            shifts__participations__localparticipation__user=self.request.user,
                            shifts__participations__state=state,
                        ),
                    )
                    for state in AbstractParticipation.States
                },
            )
            .select_related("type")
            .prefetch_related("shifts")
            .prefetch_related(Prefetch("shifts__participations"))
        )
        if self.filter_form.is_valid():
            qs = self.filter_form.filter_events(qs)
        else:
            # safeguard for not loading too many events
            qs = qs.filter(end_time__gte=timezone.now()).order_by("start_time", "end_time")
        return qs

    @cached_property
    def filter_form(self):
        return EventFilterForm(data=self.request.GET or None, request=self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["eventtypes"] = EventType.objects.all()
        ctx["filter_form"] = self.filter_form

        if (new_mode := self.request.GET.get("mode")) in {"list", "calendar", "day"}:
            self.request.session["event_list_view_mode"] = new_mode
        mode = self.request.session.get("event_list_view_mode", "list")
        ctx["mode"] = mode

        if mode == "calendar":
            ctx.update(self._get_calendar_context())
        elif mode == "day":
            ctx.update(self._get_day_context())

        return ctx

    def _get_shifts_for_calendar(self):
        return (
            Shift.objects.filter(
                event__in=get_objects_for_user(self.request.user, "core.view_event", klass=Event),
            )
            .annotate(
                can_change=Case(
                    When(
                        event_id__in=get_objects_for_user(self.request.user, ["core.change_event"]),
                        then=True,
                    ),
                    default=False,
                    output_field=BooleanField(),
                )
            )
            .select_related("event", "event__type")
            .prefetch_related("participations")
        )

    def _get_calendar_context(self):
        date = self.filter_form.get_date()
        prevyear, prevmonth = _prevmonth(date.year, date.month)
        nextyear, nextmonth = _nextmonth(date.year, date.month)

        from_time = datetime.min.replace(
            year=date.year, month=date.month, tzinfo=get_current_timezone()
        )
        to_time = datetime.min.replace(
            year=nextyear, month=nextmonth, tzinfo=get_current_timezone()
        )
        shifts = self._get_shifts_for_calendar().filter(
            start_time__gte=from_time, start_time__lt=to_time
        )

        if self.filter_form.is_valid():
            shifts = self.filter_form.filter_shifts(shifts)
        calendar = ShiftCalendar(shifts=shifts, request=self.request)

        return {
            "calendar": mark_safe(calendar.formatmonth(date.year, date.month)),
            "date": date,
            "previous_date": datetime.min.replace(year=prevyear, month=prevmonth),
            "next_date": datetime.min.replace(year=nextyear, month=nextmonth),
        }

    def _get_day_context(self):
        ctx = {}
        default_date = timezone.now()
        if self.request.session.has_key("day_calendar_last_date"):
            default_date = datetime.strptime(
                self.request.session.get("day_calendar_last_date"), "%Y-%m-%d"
            ).date()
        this_date = self.filter_form.get_date(default=default_date)
        self.request.session["day_calendar_last_date"] = this_date.strftime("%Y-%m-%d")
        ctx["previous_date"] = this_date - timedelta(days=1)
        ctx["next_date"] = this_date + timedelta(days=1)

        from_time = datetime.min.replace(
            year=this_date.year,
            month=this_date.month,
            day=this_date.day,
            tzinfo=get_current_timezone(),
        )
        to_time = from_time + timedelta(days=1, hours=3)  # show starts until 3am next day
        shifts = self._get_shifts_for_calendar().filter(
            start_time__gte=from_time, start_time__lte=to_time
        )

        if self.filter_form.is_valid():
            shifts = self.filter_form.filter_shifts(shifts)

        events = (
            Event.objects.filter(
                id__in=shifts.values_list("event_id", flat=True),
            )
            .distinct()
            .select_related("type")
            .prefetch_related(Prefetch("shifts", queryset=Shift.objects.order_by("start_time")))
        )

        css_context = self._build_day_css_context(events, shifts)
        ctx.update(
            {
                "event_list": events,
                "date": this_date,
                "hours": range(25),
                **css_context,
            }
        )
        return ctx

    def _build_day_css_context(self, events, shifts):
        """
        Build a css grid layout for the day view. Shifts are layouted in columns, with shifts of the same event
        being layouted next to each other, needing as few columns as possible.
        """
        # pylint: disable=too-many-locals
        shifts_by_event_layouted = {}
        shortest_shift_duration = timedelta.max
        for event in events:
            # If two shifts of the same event start within an hour of each other, layout them next to each other
            columns = defaultdict(list)
            for shift in event.shifts.all():
                if shift not in shifts:
                    continue
                duration = shift.end_time - shift.start_time
                shortest_shift_duration = min(shortest_shift_duration, duration)

                current_column = 0
                # search for first column that fits the shift
                while (
                    columns[current_column]
                    and shift.start_time < columns[current_column][-1].end_time
                ):
                    current_column += 1
                columns[current_column].append(shift)

            shifts_by_event_layouted[event.pk] = columns
        css_shift_tops = ""
        try:
            earliest_shift_start = min(shift.start_time for shift in shifts)
            latest_shift_end = max(shift.end_time for shift in shifts)
        except ValueError:
            # empty shifts
            earliest_shift_start = latest_shift_end = timezone.now()
            total_height = 2

        # calculate timescale based on shortest shift
        # to not make things too small, consider a maximum of 4 hours and a minimum of 15 minutes
        shortest_shift_duration_in_hours = max(
            0.25, min(4, shortest_shift_duration.total_seconds() / 3600)
        )
        # seconds per em: the shortest shift should be 3600/300 = 12em high
        time_scaling_factor = int(300 * shortest_shift_duration_in_hours)
        for shift in shifts:
            start_offset = (
                shift.start_time.timestamp() - earliest_shift_start.timestamp()
            ) / time_scaling_factor
            height = (
                shift.end_time.timestamp() - shift.start_time.timestamp()
            ) / time_scaling_factor
            # remove margin from height twice, once for top and once for bottom
            height -= 2 * 0.2

            css_shift_tops += (
                f".day-calendar-shift-{shift.pk} {{ top: {start_offset}em; height: {height}em}}\n"
            )
        total_height = (
            (latest_shift_end.timestamp() - earliest_shift_start.timestamp()) / time_scaling_factor
        ) + 2
        hour_height = 3600 / time_scaling_factor
        css_grid_columns = " "
        css_grid_headers = " "
        shift_columns = {}
        for event in events:
            max_col = 0
            for column_idx, content in enumerate(shifts_by_event_layouted[event.pk]):
                column_name = f"col-{event.pk}-{column_idx}"
                css_grid_columns += f"[{column_name}] 14em "
                shift_columns[column_name] = content
                max_col = max(max_col, column_idx)
            css_grid_headers += f".day-calendar-header-{event.pk} {{ grid-column-start: col-{event.pk}-0; grid-column-end: span {max_col + 1} }}"
        return {
            "css_grid_columns": css_grid_columns,
            "css_grid_headers": css_grid_headers,
            "css_shift_tops": css_shift_tops,
            "hour_height": str(hour_height),
            "quarter_hour_height": str(hour_height / 4),
            "half_hour_height": str(hour_height / 2),
            "shift_columns": shift_columns,
            "columns_by_event": shifts_by_event_layouted,
            "total_height": str(total_height),
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


class EventCopyView(CustomPermissionRequiredMixin, SingleObjectMixin, FormView):
    permission_required = "core.add_event"
    model = Event
    template_name = "core/event_copy.html"
    form_class = EventDuplicationForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = self.get_object()

    def form_valid(self, form):
        tz = get_current_timezone()
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
            start_date = event.get_start_time().astimezone(tz).date()
            shifts = list(event.shifts.all())
            event.pk = None
            event.save()
            assign_perm(
                "view_event",
                get_groups_with_perms(self.get_object(), only_with_perms_in=["view_event"]),
                event,
            )
            assign_perm(
                "change_event",
                get_groups_with_perms(self.get_object(), only_with_perms_in=["change_event"]),
                event,
            )
            assign_perm(
                "change_event",
                get_users_with_perms(
                    self.get_object(),
                    only_with_perms_in=["change_event"],
                    with_group_users=False,
                ),
                event,
            )

            shifts_to_create = []
            for shift in shifts:
                shift.pk = None
                # shifts on following days should have the same offset from the new date
                offset = shift.start_time.astimezone(tz).date() - start_date
                # shifts ending on the next day should end on the next day to the new date
                end_offset = (
                    shift.end_time.astimezone(tz).date() - shift.start_time.astimezone(tz).date()
                )
                shift.meeting_time = datetime.combine(
                    date.date() + offset,
                    shift.meeting_time.astimezone(tz).time(),
                    tzinfo=tz,
                )
                shift.start_time = datetime.combine(
                    date.date() + offset,
                    shift.start_time.astimezone(tz).time(),
                    tzinfo=tz,
                )
                shift.end_time = datetime.combine(
                    date.date() + offset + end_offset,
                    shift.end_time.astimezone(tz).time(),
                    tzinfo=tz,
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
