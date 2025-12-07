from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from guardian.mixins import LoginRequiredMixin

from ephios.plugins.qualification_requests.forms import QualificationRequestForm


class QualificationRequestView(LoginRequiredMixin, FormView):
    form_class = QualificationRequestForm
    template_name = "qualification_requests/qualification_requests_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.create_consequence()
        messages.success(self.request, _("Your request has been submitted."))
        return redirect(reverse("core:settings_personal_data"))
