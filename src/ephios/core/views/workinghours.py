import codecs
import csv
import datetime
from collections import Counter
from datetime import date
from itertools import chain

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import CharField, DurationField, ExpressionWrapper, F, Sum, Value
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.timezone import get_current_timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView, TemplateView, UpdateView
from django_select2.forms import Select2Widget
from guardian.shortcuts import get_objects_for_user

from ephios.core.forms.users import WorkingHourRequestForm
from ephios.core.models import EventType, LocalParticipation, UserProfile, WorkingHours
from ephios.extra.mixins import CustomCheckPermissionMixin, CustomPermissionRequiredMixin
from ephios.extra.templatetags.utils import timedelta_in_hours
from ephios.extra.widgets import CustomDateInput


class WorkingHourFilterForm(forms.Form):
    start = forms.DateField(required=False, label=_("From"), widget=CustomDateInput)
    end = forms.DateField(required=False, label=_("To"), widget=CustomDateInput)
    type = forms.ModelChoiceField(
        label=_("Event type"),
        queryset=EventType.objects.all(),
        required=False,
        widget=Select2Widget(
            attrs={
                "data-placeholder": _("Event type"),
                "classes": "w-auto",
            }
        ),
    )


def _get_filterform_with_defaults(request):
    return WorkingHourFilterForm(
        request.GET
        or {
            # intitial data for initial page laod
            # (does not use `initial` cause that only works with unbound forms)
            "start": datetime.datetime
            .now(tz=get_current_timezone())
            .replace(month=1, day=1)
            .date(),
            "end": datetime.datetime
            .now(tz=get_current_timezone())
            .replace(month=12, day=31)
            .date(),
        }
    )


def _get_working_hours_stats(start: date, end: date, eventtype: EventType | None):
    start = start or date.min
    end = end or date.max
    # pylint: disable=assignment-from-no-return
    participations = LocalParticipation.objects.filter(
        state=LocalParticipation.States.CONFIRMED,
        start_time__date__gte=start,
        end_time__date__lte=end,
    )
    workinghours = {}
    if eventtype is not None:
        participations = participations.filter(shift__event__type=eventtype)
    else:
        workinghours = (
            WorkingHours.objects
            .filter(date__gte=start, date__lte=end)
            .annotate(hour_sum=Sum("hours"), type=Value(_("Request"), output_field=CharField()))
            .values_list("user__pk", "user__display_name", "hour_sum", "type")
        )
    participations = (
        participations
        .annotate(
            duration=ExpressionWrapper(
                (F("end_time") - F("start_time")),
                output_field=DurationField(),
            ),
        )
        .annotate(hour_sum=Sum("duration"), type=F("shift__event__type__title"))
        .values_list("user__pk", "user__display_name", "hour_sum", "type")
    )

    result = {}
    c = Counter()
    for user_pk, display_name, hours, item_type in chain(participations, workinghours):
        current_sum = (
            hours.total_seconds() / (60 * 60)
            if isinstance(hours, datetime.timedelta)
            else float(hours)
        )
        c[user_pk] += current_sum
        type_counter = result[user_pk]["by_type"] if user_pk in result else Counter()
        type_counter[item_type] += current_sum
        result[user_pk] = {
            "pk": user_pk,
            "display_name": display_name,
            "hours": c[user_pk],
            "by_type": type_counter,
        }
    return sorted(result.values(), key=lambda x: x["hours"], reverse=True)


class WorkingHourOverview(CustomPermissionRequiredMixin, TemplateView):
    template_name = "core/workinghours_list.html"
    permission_required = "core.view_userprofile"

    def get_context_data(self, **kwargs):
        filter_form = _get_filterform_with_defaults(self.request)
        filter_form.is_valid()
        kwargs["filter_form"] = filter_form
        kwargs["users"] = _get_working_hours_stats(
            start=filter_form.cleaned_data.get("start"),
            end=filter_form.cleaned_data.get("end"),
            eventtype=filter_form.cleaned_data.get("type"),
        )
        kwargs["can_grant_for"] = set(
            get_objects_for_user(self.request.user, "decide_workinghours_for_group", klass=Group)
        )
        kwargs["groups_by_user"] = {
            profile.pk: set(profile.groups.all())
            for profile in UserProfile.all_objects.all().prefetch_related("groups")
        }
        return super().get_context_data(**kwargs)


class WorkingHourRequestView(LoginRequiredMixin, FormView):
    form_class = WorkingHourRequestForm
    template_name = "core/workinghours_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.create_consequence()
        messages.success(self.request, _("Your request has been submitted."))
        return redirect(reverse("core:workinghours_own"))


class CanGrantMixin:
    @cached_property
    def can_grant(self):
        """
        Return whether the current request user can grant
        working hours to the target user (which might be themselves).
        """
        if self.request.user.is_anonymous:
            return False
        can_grant_for_groups = get_objects_for_user(
            self.request.user, "decide_workinghours_for_group", klass=Group
        )
        return self._get_target_user().groups.filter(id__in=can_grant_for_groups).exists()

    def _get_target_user(self):
        """Return the user whose working hours are being managed."""
        return get_object_or_404(UserProfile, pk=self.kwargs["pk"])


class UserProfileWorkingHourView(CanGrantMixin, CustomPermissionRequiredMixin, DetailView):
    model = UserProfile
    permission_required = "core.view_userprofile"
    template_name = "core/userprofile_workinghours.html"

    def get_context_data(self, **kwargs):
        kwargs["can_grant"] = self.can_grant
        filter_form = WorkingHourFilterForm(self.request.GET)
        filter_form.is_valid()
        kwargs["filter_form"] = filter_form
        kwargs["workhour_items"] = self.get_object().get_workhour_items(
            start=filter_form.cleaned_data.get("start") or date.min,  # start/end are not required
            end=filter_form.cleaned_data.get("end") or date.max,
            eventtype=filter_form.cleaned_data.get("type"),
        )
        return super().get_context_data(**kwargs)


class OwnWorkingHourView(LoginRequiredMixin, UserProfileWorkingHourView):
    permission_required = []

    def get_object(self, queryset=None):
        return self.request.user

    def _get_target_user(self):
        return self.request.user


class PermissionDeniedIfCantGrantMixin(CanGrantMixin, CustomCheckPermissionMixin):
    def has_permission(self):
        return self.can_grant


class WorkingHourCreateView(PermissionDeniedIfCantGrantMixin, WorkingHourRequestView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["can_grant"] = True
        kwargs["user"] = self._get_target_user()
        return kwargs

    def form_valid(self, form):
        workinghour = form.save(commit=False)
        workinghour.user = form.user
        workinghour.save()
        messages.success(self.request, _("Working hours have been added."))
        return redirect(reverse("core:workinghours_list"))


class WorkingHourUpdateView(PermissionDeniedIfCantGrantMixin, UpdateView):
    model = WorkingHours
    form_class = WorkingHourRequestForm

    def get_success_url(self):
        return reverse("core:workinghours_detail", kwargs={"pk": self.object.user.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.object.user
        kwargs["can_grant"] = True
        return kwargs

    def _get_target_user(self):
        return get_object_or_404(WorkingHours, pk=self.kwargs["pk"]).user


class WorkingHourDeleteView(PermissionDeniedIfCantGrantMixin, SuccessMessageMixin, DeleteView):
    permission_required = "core.decide_workinghours_for_group"
    model = WorkingHours
    success_message = _("Working hours have been deleted.")

    def _get_target_user(self):
        return get_object_or_404(WorkingHours, pk=self.kwargs["pk"]).user

    def get_success_url(self):
        return reverse("core:workinghours_detail", kwargs={"pk": self.object.user.pk})


class WorkingHourExportView(CustomPermissionRequiredMixin, View):
    permission_required = "core.view_userprofile"

    def get(self, request, *args, **kwargs):
        filter_form = _get_filterform_with_defaults(request)
        filter_form.is_valid()
        workinghours = _get_working_hours_stats(
            start=filter_form.cleaned_data.get("start"),
            end=filter_form.cleaned_data.get("end"),
            eventtype=filter_form.cleaned_data.get("type"),
        )
        eventtypes = list(EventType.objects.all().values_list("title", flat=True)) + [_("Request")]
        rows = []
        for user in workinghours:
            row = (
                [user["display_name"]]
                + [user["by_type"][eventtype] for eventtype in eventtypes]
                + [user["hours"]]
            )
            rows.append(row)

        response = HttpResponse(
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="workinghours.csv"'},
        )
        response.write(codecs.BOM_UTF8)  # needed for excel to recognise utf-8 encoding
        writer = csv.writer(response)
        writer.writerow([_("Name")] + eventtypes + [_("Total")])
        writer.writerows(rows)
        return response


class UserProfileWorkingHourExportView(
    CustomPermissionRequiredMixin, LoginRequiredMixin, DetailView
):
    model = UserProfile

    def get_required_permissions(self, request: HttpRequest | None = None) -> list[str]:
        return [] if self.request.user == self.get_object() else ["core.view_userprofile"]

    def get(self, request, *args, **kwargs):
        filter_form = WorkingHourFilterForm(request.GET)
        filter_form.is_valid()
        workinghours = self.get_object().get_workhour_items(
            start=filter_form.cleaned_data.get("start") or date.min,  # start/end are not required
            end=filter_form.cleaned_data.get("end") or date.max,
            eventtype=filter_form.cleaned_data.get("type"),
        )[1]

        rows = []
        for entry in workinghours:
            rows.append([
                entry["date"],
                entry["reason"],
                timedelta_in_hours(entry["duration"]),
                entry["type"],
            ])

        response = HttpResponse(
            content_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{self.get_object().display_name}.csv"'
            },
        )
        response.write(codecs.BOM_UTF8)  # needed for excel to recognise utf-8 encoding
        writer = csv.writer(response)
        writer.writerow([_("Date"), _("Reason"), _("Hours"), _("Type")])
        writer.writerows(rows)
        return response
