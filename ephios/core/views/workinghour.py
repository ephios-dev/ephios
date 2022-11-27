from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import DeleteView, DetailView, FormView, TemplateView, UpdateView

from ephios.core.forms.users import WorkingHourRequestForm
from ephios.core.models import UserProfile, WorkingHours
from ephios.extra.mixins import CustomPermissionRequiredMixin


class WorkingHourOverview(CustomPermissionRequiredMixin, TemplateView):
    template_name = "core/workinghour_list.html"
    permission_required = "core.view_userprofile"

    def get_context_data(self, **kwargs):
        kwargs["userprofiles"] = sorted(
            [
                (userprofile, userprofile.get_workhour_items())
                for userprofile in UserProfile.objects.all()
            ],
            key=lambda x: x[1][0],
            reverse=True,
        )
        return super().get_context_data(**kwargs)


class OwnWorkingHourView(LoginRequiredMixin, DetailView):
    template_name = "core/userprofile_workinghours.html"

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        kwargs["own_profile"] = True
        kwargs["can_grant"] = self.request.user.has_perm("core.grant_working_hours")
        return super().get_context_data(**kwargs)


class UserProfileWorkingHourView(CustomPermissionRequiredMixin, DetailView):
    model = UserProfile
    permission_required = "core.view_userprofile"
    template_name = "core/userprofile_workinghours.html"

    def get_context_data(self, **kwargs):
        kwargs["can_grant"] = self.request.user.has_perm("core.grant_working_hours")
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


class WorkingHourCreateView(CustomPermissionRequiredMixin, WorkingHourRequestView):
    permission_required = "core.grant_working_hours"

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


class WorkingHourUpdateView(CustomPermissionRequiredMixin, UpdateView):
    permission_required = "core.grant_working_hours"
    model = WorkingHours
    form_class = WorkingHourRequestForm

    def get_success_url(self):
        return reverse("core:workinghour_detail", kwargs={"pk": self.object.user.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["request"] = self.request
        kwargs["can_grant"] = True
        return kwargs


class WorkingHourDeleteView(CustomPermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    permission_required = "core.grant_working_hours"
    model = WorkingHours
    success_message = _("Working hours have been deleted.")

    def get_success_url(self):
        return reverse("core:workinghour_detail", kwargs={"pk": self.object.user.pk})
