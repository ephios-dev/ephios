from django import forms
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.detail import SingleObjectMixin

from ephios.event_management.models import AbstractParticipation, Shift
from ephios.extra.permissions import CustomPermissionRequiredMixin
from ephios.plugins.basesignup.signup.instant import SimpleQualificationsRequiredSignupMethod

DispositionParticipationFormset = forms.modelformset_factory(
    model=AbstractParticipation,
    fields=["state"],
    extra=0,
    can_order=False,
    can_delete=False,
    widgets={
        "state": forms.HiddenInput(attrs={"class": "state-input"}),
    },
)


class RequestConfirmDispositionView(CustomPermissionRequiredMixin, SingleObjectMixin, TemplateView):
    model = Shift
    permission_required = "event_management.change_event"
    template_name = "basesignup/requestconfirm_signup/disposition.html"

    def get_permission_object(self):
        self.object: Shift = self.get_object()
        return self.object.event

    def get_formset(self):
        return DispositionParticipationFormset(
            self.request.POST or None, queryset=self.object.participations
        )

    def get(self, request, *args, **kwargs):
        self.object: Shift = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object: Shift = self.get_object()
        formset = self.get_formset()
        if formset.is_valid():
            formset.save()
            return redirect(self.object.event.get_absolute_url())
        return self.get(request, *args, **kwargs, formset=formset)

    def get_context_data(self, **kwargs):
        kwargs.setdefault("formset", self.get_formset())
        kwargs.setdefault("states", AbstractParticipation.States)
        return super().get_context_data(**kwargs)


class RequestConfirmSignupMethod(SimpleQualificationsRequiredSignupMethod):
    slug = "request_confirm"
    verbose_name = _("Request and confirm")
    description = _(
        """This method lets people request participation. Responsibles can then confirm the participation."""
    )
    registration_button_text = _("Request")
    signup_success_message = _("You have successfully requested a participation for {shift}.")
    signup_error_message = _("Requesting a participation failed: {error}")

    def render_shift_state(self, request):
        participations = self.shift.participations.filter(
            state__in={
                AbstractParticipation.States.REQUESTED,
                AbstractParticipation.States.CONFIRMED,
            }
        )
        return get_template("basesignup/requestconfirm_signup/fragment_state.html").render(
            {
                "shift": self.shift,
                "requested_participants": (
                    p.participant
                    for p in participations.filter(state=AbstractParticipation.States.REQUESTED)
                ),
                "confirmed_participants": (
                    p.participant
                    for p in participations.filter(state=AbstractParticipation.States.CONFIRMED)
                ),
                "disposition_url": (
                    reverse(
                        "basesignup:shift_disposition_requestconfirm", kwargs=dict(pk=self.shift.pk)
                    )
                    if request.user.has_perm("event_management.change_event", obj=self.shift.event)
                    else None
                ),
            }
        )

    def perform_signup(self, participant, **kwargs):
        participation = super().perform_signup(participant, **kwargs)
        participation.state = AbstractParticipation.States.REQUESTED
        participation.save()
        return participation
