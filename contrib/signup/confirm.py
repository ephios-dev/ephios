from django import forms
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from contrib.signup.instant import SimpleQualificationsRequiredSignupMethod
from event_management.models import AbstractParticipation
from event_management.signup import (
    BaseSignupMethod,
    register_signup_methods,
    ParticipationError,
)
from user_management.models import Qualification


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
        participations = self.shift.get_participations(
            with_state_in={AbstractParticipation.REQUESTED, AbstractParticipation.CONFIRMED}
        )
        bool(participations)  # evaluate queryset
        return get_template("jepcontrib/signup_requestconfirm_state.html").render(
            {
                "shift": self.shift,
                "requested_participators": (
                    p.participator
                    for p in participations.filter(state=AbstractParticipation.REQUESTED)
                ),
                "confirmed_participators": (
                    p.participator
                    for p in participations.filter(state=AbstractParticipation.CONFIRMED)
                ),
            }
        )

    def perform_signup(self, participator, **kwargs):
        participation = super().perform_signup(participator, **kwargs)
        participation.state = AbstractParticipation.REQUESTED
        participation.save()
        return participation
