from django import forms
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup.methods import ActionDisallowedError, BaseSignupMethod
from ephios.plugins.basesignup.signup.common import RenderParticipationPillsShiftStateMixin


class NoSelfserviceSignupMethod(RenderParticipationPillsShiftStateMixin, BaseSignupMethod):
    slug = "no_selfservice"
    verbose_name = _("No Signup (only disposition)")
    description = _("""This method allows no signup by users.""")
    uses_requested_state = False

    @property
    def configuration_form_class(self):
        class ConfigurationForm(super().configuration_form_class):
            no_selfservice_explanation = forms.CharField(
                label=_("Explanation"),
                required=False,
                initial="",
            )

        return ConfigurationForm

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        raise TypeError(f"{self.__class__} does not support signup")

    @staticmethod
    def signup_is_disabled(method, participant):
        return ActionDisallowedError(
            method.configuration.no_selfservice_explanation
            or _("Signup for this shift is disabled.")
        )

    @property
    def _signup_checkers(self):
        return [
            self.signup_is_disabled,
        ]

    @property
    def _decline_checkers(self):
        return [
            self.signup_is_disabled,
        ]
