from bootstrap4.widgets import RadioSelectButtonGroup
from django import forms
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from contrib.signup.instant import SimpleQualificationsRequiredSignupMethod
from event_management.models import AbstractParticipation, Shift
from guardian.mixins import PermissionRequiredMixin

DispositionParticipationFormset = forms.modelformset_factory(
    model=AbstractParticipation,
    fields=["state"],
    extra=0,
    can_order=False,
    can_delete=False,
    widgets={"state": forms.HiddenInput(attrs={"class": "state-input"}),},
)


class RequestConfirmDispositionView(PermissionRequiredMixin, SingleObjectMixin, TemplateView):
    model = Shift
    permission_required = "event_management.change_event"
    accept_global_perms = True
    template_name = "jepcontrib/requestconfirm_signup/disposition.html"

    def get_permission_object(self):
        self.object: Shift = self.get_object()
        return self.object.event

    def get_formset(self):
        return DispositionParticipationFormset(
            self.request.POST or None, queryset=self.object.participations
        )

    def post(self, request, *args, **kwargs):
        formset = self.get_formset()
        if formset.is_valid():
            formset.save()
            return redirect(self.object.event.get_absolute_url())
        return self.get(request, *args, **kwargs, formset=formset)

    def get_context_data(self, **kwargs):
        kwargs.setdefault("formset", self.get_formset())
        kwargs.setdefault("states", AbstractParticipation)
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
            state__in={AbstractParticipation.REQUESTED, AbstractParticipation.CONFIRMED}
        )
        return get_template("jepcontrib/requestconfirm_signup/fragment_state.html").render(
            {
                "shift": self.shift,
                "requested_participators": (
                    p.participant
                    for p in participations.filter(state=AbstractParticipation.REQUESTED)
                ),
                "confirmed_participators": (
                    p.participant
                    for p in participations.filter(state=AbstractParticipation.CONFIRMED)
                ),
                "disposition_url": (
                    reverse(
                        "contrib:shift_disposition_requestconfirm", kwargs=dict(pk=self.shift.pk)
                    )
                    if request.user.has_perm("event_management.change_event", obj=self.shift.event)
                    else None
                ),
            }
        )

    def perform_signup(self, participator, **kwargs):
        participation = super().perform_signup(participator, **kwargs)
        participation.state = AbstractParticipation.REQUESTED
        participation.save()
        return participation
