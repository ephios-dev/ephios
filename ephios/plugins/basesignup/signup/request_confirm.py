from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup import BaseSignupMethod
from ephios.plugins.basesignup.signup.common import (
    MinMaxParticipantsMixin,
    QualificationsRequiredSignupMixin,
)


class RequestConfirmSignupMethod(
    QualificationsRequiredSignupMixin, MinMaxParticipantsMixin, BaseSignupMethod
):
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
        return get_template("basesignup/request_confirm/fragment_state.html").render(
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
                    reverse("core:shift_disposition", kwargs=dict(pk=self.shift.pk))
                    if request.user.has_perm("core.change_event", obj=self.shift.event)
                    else None
                ),
            }
        )

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        participation.state = AbstractParticipation.States.REQUESTED
        return participation
