from django import forms
from django.utils.translation import gettext_lazy as _

from ephios.core.signup.flow.base import BaseSignupFlow
from ephios.core.signup.flow.participant_validation import NoSignupSignupActionValidator
from ephios.core.signup.forms import SignupConfigurationForm


class ManualSignupActionValidator(NoSignupSignupActionValidator):
    def get_no_signup_allowed_message(self):
        return self.shift.signup_flow.configuration.no_selfservice_explanation or _(
            "Signup for this shift is disabled."
        )


class ManualSignupConfigurationForm(SignupConfigurationForm):
    no_selfservice_explanation = forms.CharField(
        label=_("Explanation"),
        help_text=_(
            "If you want to explain why self-service signup is disabled, you can do so here."
        ),
        required=False,
        initial="",
    )


class ManualSignupFlow(BaseSignupFlow):
    """
    Signup flow for manual signups.
    """

    slug = "manual"
    verbose_name = _("Manual disposition")
    description = _("Participants are manually added to the shift by the responsibles.")
    registration_button_text = None
    uses_requested_state = False
    signup_action_validator_class = ManualSignupActionValidator
    configuration_form_class = ManualSignupConfigurationForm

    def _configure_participation(self, participation, **kwargs):
        raise TypeError("Manual signup flow does not support signup.")
