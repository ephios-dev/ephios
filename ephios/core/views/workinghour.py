import datetime
from collections import Counter
from datetime import date
from itertools import chain
from typing import Optional

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import DurationField, ExpressionWrapper, F, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.views.generic import DeleteView, DetailView, FormView, TemplateView, UpdateView
from django_select2.forms import Select2Widget
from guardian.shortcuts import get_objects_for_user

from ephios.core.forms.users import WorkingHourRequestForm
from ephios.core.models import EventType, LocalParticipation, UserProfile, WorkingHours
from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.extra.widgets import CustomDateInput


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


class WorkingHourOverview(CustomPermissionRequiredMixin, TemplateView):
    template_name = "core/workinghours_list.html"
    permission_required = "core.view_userprofile"

    def _get_working_hours_stats(self, start: date, end: date, eventtype: Optional[EventType]):
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
                WorkingHours.objects.filter(date__gte=start, date__lte=end)
                .annotate(hour_sum=Sum("hours"))
                .values_list("user__pk", "user__display_name", "hour_sum")
            )
        participations = (
            participations.annotate(
                duration=ExpressionWrapper(
                    (F("end_time") - F("start_time")),
                    output_field=DurationField(),
                ),
            )
            .annotate(hour_sum=Sum("duration"))
            .values_list("user__pk", "user__display_name", "hour_sum")
        )

        result = {}
        c = Counter()
        for user_pk, display_name, hours in chain(participations, workinghours):
            current_sum = (
                hours.total_seconds() / (60 * 60)
                if isinstance(hours, datetime.timedelta)
                else float(hours)
            )
            c[user_pk] += current_sum
            result[user_pk] = {
                "pk": user_pk,
                "display_name": display_name,
                "hours": c[user_pk],
            }
        return sorted(result.values(), key=lambda x: x["hours"], reverse=True)

    def get_context_data(self, **kwargs):
        filter_form = WorkingHourFilterForm(
            self.request.GET
            or {
                # intitial data for initial page laod
                # (does not use `initial` cause that only works with unbound forms)
                "start": date.today().replace(month=1, day=1),
                "end": date.today().replace(month=12, day=31),
            }
        )
        filter_form.is_valid()
        kwargs["filter_form"] = filter_form
        kwargs["users"] = self._get_working_hours_stats(
            start=filter_form.cleaned_data.get("start") or date.min,  # start/end are not required
            end=filter_form.cleaned_data.get("end") or date.max,
            eventtype=filter_form.cleaned_data.get("type"),
        )
        kwargs["can_grant_for"] = set(
            get_objects_for_user(self.request.user, "decide_workinghours_for_group", klass=Group)
        )
        kwargs["groups_by_user"] = {
            profile.pk: set(profile.groups.all())
            for profile in UserProfile.objects.all().prefetch_related("groups")
        }
        return super().get_context_data(**kwargs)


class OwnWorkingHourView(LoginRequiredMixin, DetailView):
    template_name = "core/userprofile_workinghours.html"

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        kwargs["own_profile"] = True
        grant_ids = get_objects_for_user(
            self.request.user, "decide_workinghours_for_group", klass=Group
        ).values_list("id", flat=True)
        kwargs["can_grant"] = self.request.user.groups.filter(id__in=grant_ids).exists()
        return super().get_context_data(**kwargs)


class UserProfileWorkingHourView(CanGrantMixin, CustomPermissionRequiredMixin, DetailView):
    model = UserProfile
    permission_required = "core.view_userprofile"
    template_name = "core/userprofile_workinghours.html"

    def get_context_data(self, **kwargs):
        kwargs["can_grant"] = self.can_grant
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


class WorkingHourCreateView(CanGrantMixin, CustomPermissionRequiredMixin, WorkingHourRequestView):
    def has_permission(self):
        return self.can_grant

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


class WorkingHourUpdateView(CanGrantMixin, CustomPermissionRequiredMixin, UpdateView):
    model = WorkingHours
    form_class = WorkingHourRequestForm

    def has_permission(self):
        return self.can_grant

    def get_success_url(self):
        return reverse("core:workinghours_detail", kwargs={"pk": self.object.user.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.object.user
        kwargs["can_grant"] = True
        return kwargs

    def _get_target_user(self):
        return get_object_or_404(WorkingHours, pk=self.kwargs["pk"]).user


class WorkingHourDeleteView(
    CanGrantMixin, CustomPermissionRequiredMixin, SuccessMessageMixin, DeleteView
):
    permission_required = "core.decide_workinghours_for_group"
    model = WorkingHours
    success_message = _("Working hours have been deleted.")

    def _get_target_user(self):
        return get_object_or_404(WorkingHours, pk=self.kwargs["pk"]).user

    def has_permission(self):
        return self.can_grant

    def get_success_url(self):
        return reverse("core:workinghours_detail", kwargs={"pk": self.object.user.pk})
