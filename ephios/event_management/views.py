import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Max, Min
from django.forms import DateField
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.timezone import get_current_timezone, get_default_timezone, make_aware
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView
from guardian.shortcuts import assign_perm, get_objects_for_user, get_users_with_perms
from recurrence.forms import RecurrenceField

from ephios.event_management.forms import EventDuplicationForm, EventForm, ShiftForm
from ephios.event_management.models import Event, Shift
from ephios.extra.permissions import CustomPermissionRequiredMixin, get_groups_with_perms


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "event_management/home.html"


class EventListView(LoginRequiredMixin, ListView):
    model = Event

    def get_queryset(self):
        return (
            get_objects_for_user(self.request.user, "event_management.view_event")
            .annotate(
                start_time=Min("shifts__start_time"),
                end_time=Max("shifts__end_time"),
            )
            .filter(end_time__gte=timezone.now())
            .select_related("type")
            .order_by("start_time")
        )


class EventDetailView(CustomPermissionRequiredMixin, DetailView):
    model = Event
    permission_required = "event_management.view_event"

    def get_queryset(self):
        if self.request.user.has_perm("event_management.add_event"):
            return Event.all_objects.all()
        return Event.objects.all()


class EventUpdateView(CustomPermissionRequiredMixin, UpdateView):
    model = Event
    queryset = Event.all_objects.all()
    permission_required = "event_management.change_event"

    def get_form(self, form_class=None):
        return EventForm(
            data=self.request.POST or None, user=self.request.user, instance=self.object
        )


class EventCreateView(CustomPermissionRequiredMixin, CreateView):
    template_name = "event_management/event_form.html"
    permission_required = "event_management.add_event"
    accept_object_perms = False

    def get_form(self, form_class=None):
        return EventForm(
            data=self.request.POST or None,
            user=self.request.user,
            initial={
                "responsible_users": get_user_model().objects.filter(pk=self.request.user.pk),
                "responsible_groups": Group.objects.none(),
                "visible_for": get_objects_for_user(
                    self.request.user, "publish_event_for_group", klass=Group
                ),
            },
        )

    def get_context_data(self, **kwargs):
        inactive_events = Event.all_objects.filter(active=False)
        kwargs.setdefault("inactive_events", inactive_events)
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse("event_management:event_createshift", kwargs={"pk": self.object.pk})


class EventActivateView(CustomPermissionRequiredMixin, SingleObjectMixin, View):
    permission_required = "event_management.add_event"
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
        return redirect(reverse("event_management:event_detail", kwargs={"pk": event.pk}))


class EventDeleteView(CustomPermissionRequiredMixin, DeleteView):
    queryset = Event.all_objects.all()
    permission_required = "event_management.delete_event"
    success_url = reverse_lazy("event_management:event_list")


class EventBulkDeleteView(CustomPermissionRequiredMixin, TemplateResponseMixin, View):
    permission_required = "event_management.delete_event"
    template_name = "event_management/event_bulk_delete.html"

    def post(self, request, *args, **kwargs):
        events = Event.objects.filter(pk__in=request.POST.getlist("bulk_action"))
        if not events:
            messages.info(request, _("No events were selected for deletion."))
            return redirect(reverse("event_management:event_list"))
        if request.POST.get("confirm"):
            events.delete()
            messages.info(request, _("The selected events have been deleted."))
            return redirect(reverse("event_management:event_list"))
        return self.render_to_response({"events": events})


class EventArchiveView(CustomPermissionRequiredMixin, ListView):
    permission_required = "event_management.view_past_event"
    model = Event
    template_name = "event_management/event_archive.html"

    def get_queryset(self):
        return (
            get_objects_for_user(self.request.user, "event_management.view_event")
            .annotate(
                start_time=Min("shifts__start_time"),
                end_time=Max("shifts__end_time"),
            )
            .filter(end_time__lt=timezone.now())
            .select_related("type")
            .order_by("-start_time")
        )


class EventCopyView(CustomPermissionRequiredMixin, SingleObjectMixin, FormView):
    permission_required = "event_management.add_event"
    model = Event
    template_name = "event_management/event_copy.html"
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
        return redirect(reverse("event_management:event_list"))


class RRuleOccurrenceView(CustomPermissionRequiredMixin, View):
    permission_required = "event_management.add_event"

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


class ShiftCreateView(CustomPermissionRequiredMixin, TemplateView):
    permission_required = "event_management.change_event"
    template_name = "event_management/shift_form.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.event = get_object_or_404(Event.all_objects, pk=self.kwargs.get("pk"))

    def get_permission_object(self):
        return self.event

    def get_shift_form(self):
        return ShiftForm(self.request.POST or None)

    def get_context_data(self, **kwargs):
        kwargs.setdefault("event", self.event)
        kwargs.setdefault("form", self.get_shift_form())
        kwargs.setdefault("configuration_form", "")
        return super().get_context_data(**kwargs)

    def post(self, *args, **kwargs):
        form = self.get_shift_form()
        try:
            from ephios.event_management.signup import signup_method_from_slug

            signup_method = signup_method_from_slug(self.request.POST["signup_method_slug"])
            configuration_form = signup_method.get_configuration_form(self.request.POST)
        except ValueError as e:
            raise ValidationError(e) from e
        if form.is_valid() and configuration_form.is_valid():
            shift = form.save(commit=False)
            shift.event = self.event
            shift.signup_configuration = configuration_form.cleaned_data
            shift.save()
            if "addAnother" in self.request.POST:
                return redirect(
                    reverse(
                        "event_management:event_createshift", kwargs={"pk": self.kwargs.get("pk")}
                    )
                )
            try:
                self.event.activate()
                messages.success(
                    self.request,
                    _("The event {title} has been saved.").format(title=self.event.title),
                )
            except ValidationError as e:
                messages.error(self.request, e)
            return redirect(self.event.get_absolute_url())
        return self.render_to_response(
            self.get_context_data(
                form=form,
                configuration_form=signup_method.render_configuration_form(form=configuration_form),
            )
        )


class ShiftConfigurationFormView(View):
    def get(self, request, *args, **kwargs):
        from ephios.event_management.signup import signup_method_from_slug

        signup_method = signup_method_from_slug(self.kwargs.get("slug"))
        return HttpResponse(signup_method.render_configuration_form())


class ShiftUpdateView(CustomPermissionRequiredMixin, SingleObjectMixin, TemplateView):
    model = Shift
    template_name = "event_management/shift_form.html"
    permission_required = "event_management.change_event"

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
        return self.object.signup_method.render_configuration_form(data=self.request.POST or None)

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
            from ephios.event_management.signup import signup_method_from_slug

            signup_method = signup_method_from_slug(self.request.POST["signup_method_slug"])
            configuration_form = signup_method.get_configuration_form(self.request.POST)
        except ValueError as e:
            raise ValidationError(e) from e
        if form.is_valid() and configuration_form.is_valid():
            shift = form.save(commit=False)
            shift.signup_configuration = configuration_form.cleaned_data
            shift.save()
            if "addAnother" in self.request.POST:
                return redirect(
                    reverse("event_management:event_createshift", kwargs={"pk": shift.event.pk})
                )
            messages.success(
                self.request, _("The shift {shift} has been saved.").format(shift=shift)
            )
            return redirect(self.object.event.get_absolute_url())
        return self.render_to_response(
            self.get_context_data(
                form=form,
                configuration_form=signup_method.render_configuration_form(form=configuration_form),
            )
        )


class ShiftDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "event_management.change_event"
    model = Shift

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = self.get_object()

    def delete(self, request, *args, **kwargs):
        if self.object.event.shifts.count() == 1:
            messages.error(self.request, _("You cannot delete the last shift!"))
            return redirect(self.object.event.get_absolute_url())
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        messages.success(self.request, _("The shift has been deleted."))
        return self.object.event.get_absolute_url()

    def get_permission_object(self):
        return self.object.event


class SignupMethodViewMixin(SingleObjectMixin):
    model = Shift

    def dispatch(self, request, *args, **kwargs):
        return self.get_object().signup_method.signup_view(request, *args, **kwargs)


class ShiftSignupView(CustomPermissionRequiredMixin, SignupMethodViewMixin, View):
    permission_required = "event_management.view_event"

    def get_permission_object(self):
        return self.get_object().event
