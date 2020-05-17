from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import (
    ListView,
    DetailView,
    UpdateView,
    DeleteView,
    RedirectView,
)

from service_management.models import Service, Shift, Participation


class ListView(LoginRequiredMixin, ListView):
    model = Service


class DetailView(LoginRequiredMixin, DetailView):
    model = Service


class UpdateView(LoginRequiredMixin, UpdateView):
    model = Service


class DeleteView(LoginRequiredMixin, DeleteView):
    model = Service


class ShiftRegisterView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        shift = get_object_or_404(Shift, id=self.kwargs["pk"])
        if self.request.user.is_minor and not shift.minors_allowed:
            messages.error(
                request=self.request, message="Minors are not allowed for this shift."
            )
        else:
            try:
                Participation(user=self.request.user, shift=shift).save()
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
            "service_management:service_detail", kwargs={"pk": shift.service.id}
        )
