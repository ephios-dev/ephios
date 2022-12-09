import datetime
from collections import Counter
from itertools import chain

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import DurationField, ExpressionWrapper, F, Sum
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import DeleteView, DetailView, FormView, TemplateView, UpdateView
from guardian.shortcuts import get_objects_for_user

from ephios.core.forms.users import WorkingHourRequestForm
from ephios.core.models import LocalParticipation, UserProfile, WorkingHours
from ephios.extra.mixins import CustomPermissionRequiredMixin


class WorkingHourPermissionMixin:
    def setup(self, request, *args, **kwargs):
        result = super().setup(request, *args, **kwargs)
        self.target_user = UserProfile.objects.get(pk=self.kwargs["pk"])
        grant_ids = get_objects_for_user(
            self.request.user, "decide_workinghours_for_group", klass=Group
        ).values_list("id", flat=True)
        self.can_grant = self.target_user.groups.filter(id__in=grant_ids).exists()
        return result


class WorkingHourOverview(CustomPermissionRequiredMixin, TemplateView):
    template_name = "core/workinghour_list.html"
    permission_required = "core.view_userprofile"

    def get_context_data(self, **kwargs):
        today = datetime.datetime.today()
        year = int(self.request.GET.get("year", today.year))
        # users = UserProfile.objects.annotate(
        #     hour_sum=Sum(ExpressionWrapper(
        #             (F("participations__shift__start_time") - F("participations__shift__end_time")),
        #             output_field=DurationField(),
        #         ), filter=Q(participations__state=LocalParticipation.States.CONFIRMED, participations__shift__start_time__year=year)
        # ))
        # participations = LocalParticipation.objects.filter(
        #     state=LocalParticipation.States.CONFIRMED,
        # ).annotate(duration=ExpressionWrapper(
        #             (F("end_time") - F("start_time")),
        #             output_field=DurationField(),
        #         ),).values("user").annotate(hour_sum=Sum("duration")).values_list("user", "hour_sum")
        participations = (
            LocalParticipation.objects.filter(
                state=LocalParticipation.States.CONFIRMED,
                start_time__year=year,
                finished=True,
            )
            .annotate(
                duration=ExpressionWrapper(
                    (F("end_time") - F("start_time")),
                    output_field=DurationField(),
                ),
            )
            .annotate(hour_sum=Sum("duration"))
            .values_list("user__pk", "user__first_name", "user__last_name", "hour_sum")
        )
        workinghours = (
            WorkingHours.objects.filter(date__year=year)
            .annotate(hour_sum=Sum("hours"))
            .values_list("user__pk", "user__first_name", "user__last_name", "hour_sum")
        )
        result = {}
        c = Counter()
        for user_pk, first_name, last_name, hours in chain(participations, workinghours):
            current_sum = (
                hours.total_seconds() / (60 * 60)
                if isinstance(hours, datetime.timedelta)
                else float(hours)
            )
            c[user_pk] += current_sum
            result[user_pk] = {
                "pk": user_pk,
                "first_name": first_name,
                "last_name": last_name,
                "hours": c[user_pk],
            }
        kwargs["users"] = sorted(result.values(), key=lambda x: x["hours"], reverse=True)
        kwargs["year"] = year
        kwargs["next_year"] = year + 1 if year < today.year else None
        kwargs["previous_year"] = year - 1
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


class UserProfileWorkingHourView(
    WorkingHourPermissionMixin, CustomPermissionRequiredMixin, DetailView
):
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
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        form.create_consequence()
        messages.success(self.request, _("Your request has been submitted."))
        return redirect(reverse("core:workinghour_own"))


class WorkingHourCreateView(
    WorkingHourPermissionMixin, CustomPermissionRequiredMixin, WorkingHourRequestView
):
    def has_permission(self):
        return self.can_grant

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["can_grant"] = True
        kwargs["user"] = UserProfile.objects.get(pk=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        workinghour = form.save(commit=False)
        workinghour.user = form.user
        workinghour.save()
        messages.success(self.request, _("Working hours have been added."))
        return redirect(reverse("core:workinghour_list"))


class WorkingHourUpdateView(WorkingHourPermissionMixin, CustomPermissionRequiredMixin, UpdateView):
    model = WorkingHours
    form_class = WorkingHourRequestForm

    def has_permission(self):
        return self.can_grant

    def get_success_url(self):
        return reverse("core:workinghour_detail", kwargs={"pk": self.object.user.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["request"] = self.request
        kwargs["can_grant"] = True
        return kwargs


class WorkingHourDeleteView(
    WorkingHourPermissionMixin, CustomPermissionRequiredMixin, SuccessMessageMixin, DeleteView
):
    permission_required = "core.decide_workinghours_for_group"
    model = WorkingHours
    success_message = _("Working hours have been deleted.")

    def has_permission(self):
        return self.can_grant

    def get_success_url(self):
        return reverse("core:workinghour_detail", kwargs={"pk": self.object.user.pk})
