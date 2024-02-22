from django.utils.translation import gettext_lazy as _

from ephios.core.signup.flow.base import BaseSignupFlow, BasicSignupFlowConfigurationForm
from ephios.core.signup.flow.participant_validation import BasicSignupActionValidator


class ParticipantSignupActionValidator(BasicSignupActionValidator):
    pass


class ParticipantSignupConfigurationForm(BasicSignupFlowConfigurationForm):
    pass


class RequestConfirmSignupFlow(BaseSignupFlow):
    slug = "request_confirm"
    verbose_name = _("Request and confirm")
    description = _(
        "Participants can request participation. Responsibles can confirm or reject requests."
    )
    registration_button_text = _("Request")
    uses_requested_state = True
    signup_action_validator_class = ParticipantSignupActionValidator
    configuration_form_class = ParticipantSignupConfigurationForm

    def _configure_participation(self, participation, **kwargs):
        participation.state = participation.States.REQUESTED
        return participation
