from django import forms
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup.forms import AbstractSignupMethodConfigurationForm
from ephios.core.signup.methods import BaseSignupMethod
from ephios.plugins.basesignup.signup.common import (
    NoSignupSignupActionValidator,
    NoSignupSignupView,
    RenderParticipationPillsShiftStateMixin,
)


class NoSelfserviceConfigurationForm(AbstractSignupMethodConfigurationForm):
    no_selfservice_explanation = forms.CharField(
        label=_("Explanation"),
        required=False,
        initial="",
    )


class NoSelfserviceSignupActionValidator(NoSignupSignupActionValidator):
    def get_no_signup_allowed_message(self):
        return self.signup_method.configuration.no_selfservice_explanation or _(
            "Signup for this shift is disabled."
        )


class NoSelfserviceSignupMethod(RenderParticipationPillsShiftStateMixin, BaseSignupMethod):
    slug = "no_selfservice"
    verbose_name = _("No Signup (only disposition)")
    description = _("""This method allows no signup by users.""")
    uses_requested_state = False
    configuration_form_class = NoSelfserviceConfigurationForm
    signup_view_class = NoSignupSignupView
    signup_action_validator_class = NoSelfserviceSignupActionValidator

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        raise TypeError(f"{self.__class__} does not support signup")
