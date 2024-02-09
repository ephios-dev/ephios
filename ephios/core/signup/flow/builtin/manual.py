from django import forms
from django.utils.translation import gettext_lazy as _

from ephios.core.signup.flow.base import BaseSignupFlow, BaseSignupFlowConfigurationForm
from ephios.core.signup.flow.builtin import NoSignupSignupActionValidator


class ManualSignupActionValidator(NoSignupSignupActionValidator):
    def get_no_signup_allowed_message(self):
        return self.shift.signup_flow.configuration.no_selfservice_explanation or _(
            "Signup for this shift is disabled."
        )


class ManualSignupConfigurationForm(BaseSignupFlowConfigurationForm):
    no_selfservice_explanation = forms.CharField(
        label=_("Explanation"),
        required=False,
        initial="",
    )


class ManualSignupFlow(BaseSignupFlow):
    """
    Signup flow for manual signups.
    """

    slug = "manual"
    verbose_name = _("Manual")
    description = _("Sign up by the organizer")
    registration_button_text = _("Sign up")
    uses_requested_state = False
    signup_action_validator_class = ManualSignupActionValidator
    configuration_form_class = ManualSignupConfigurationForm

    def _configure_participation(self, participation, **kwargs):
        raise TypeError("Manual signup flow does not support signup.")
