import typing

from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ephios.core.models import AbstractParticipation
from ephios.core.signup.methods import BaseSignupMethod
from ephios.plugins.basesignup.signup.common import QualificationMinMaxBaseSignupMethod

_Base = BaseSignupMethod if typing.TYPE_CHECKING else object


class AutomaticConfirmationMixin(_Base):
    """mixin for signup methods where an instant confirmation can be optionally enabled"""

    @property
    def configuration_form_class(self):
        class ConfigurationForm(super().configuration_form_class):
            instant_confirmation = forms.BooleanField(
                required=False,
                initial=False,
                label=_("Instant confirmation"),
                help_text=_(
                    "Instantly confirm every signup instead bypassing disposition and request state"
                ),
            )

        return ConfigurationForm

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        if self.configuration.instant_confirmation:
            participation.state = AbstractParticipation.States.CONFIRMED
        else:
            participation.state = AbstractParticipation.States.REQUESTED
        return participation

    @property
    def signup_view_class(self):
        if self.configuration.instant_confirmation:
            return super().signup_view_class

        class SignupView(super().signup_view_class):
            signup_success_message = _(
                "You have successfully requested a participation for {shift}."
            )
            signup_error_message = _("Requesting a participation failed: {error}")

        return SignupView

    @property
    def registration_button_text(self):
        if self.configuration.instant_confirmation:
            return super().registration_button_text
        return pgettext_lazy("signup button text", "Request")

    @property
    def uses_requested_state(self):
        return not self.configuration.instant_confirmation


class SimpleQualificationRequiredSignupMethod(
    AutomaticConfirmationMixin, QualificationMinMaxBaseSignupMethod
):
    slug = "simple_qualification_required"
    verbose_name = _("Require uniform qualification")
    description = _("""This method requires all participants to have the same qualification.""")
