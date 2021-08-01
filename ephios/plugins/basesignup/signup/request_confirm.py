from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.plugins.basesignup.signup.common import QualificationMinMaxBaseSignupMethod


class RequestConfirmSignupMethod(QualificationMinMaxBaseSignupMethod):
    slug = "request_confirm"
    verbose_name = _("Request and confirm")
    description = _(
        """This method lets people request participation. Responsibles can then confirm the participation."""
    )
    registration_button_text = _("Request")
    signup_success_message = _("You have successfully requested a participation for {shift}.")
    signup_error_message = _("Requesting a participation failed: {error}")

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        participation.state = AbstractParticipation.States.REQUESTED
        return participation
