from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin

from ephios.core.consequences import ConsequenceError, editable_consequences
from ephios.core.forms.users import WorkingHourRequestForm
from ephios.core.models import Consequence


class ConsequenceUpdateView(LoginRequiredMixin, SingleObjectMixin, View):
    def get_queryset(self):
        return editable_consequences(self.request.user)

    def post(self, request, *args, **kwargs):
        consequence = self.get_object()
        fail_reason = None
        if request.POST["action"] == "deny":
            consequence.deny(request.user)
        elif request.POST["action"] == "confirm":
            try:
                consequence.confirm(request.user)
            except ConsequenceError as e:
                fail_reason = str(e)

        if request.is_ajax():
            return JsonResponse(
                {
                    "state": consequence.state,
                    "fail_reason": fail_reason,
                }
            )
        if consequence.state == Consequence.States.FAILED:
            messages.error(request, _("There was an error performing that action."))
        return redirect("core:index")


class WorkingHourRequestView(LoginRequiredMixin, FormView):
    form_class = WorkingHourRequestForm
    template_name = "core/workinghour_request.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        form.create_consequence()
        messages.success(self.request, _("Your request has been submitted."))
        return redirect(reverse("core:profile"))
