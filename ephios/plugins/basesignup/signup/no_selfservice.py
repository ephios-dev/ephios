from django import forms
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup import BaseSignupMethod, ParticipationError
from ephios.plugins.basesignup.signup.common import render_basic_participation_pills_shift_state


class NoSelfserviceSignupMethod(BaseSignupMethod):
    slug = "no_selfservice"
    verbose_name = _("No Signup (only disposition)")
    description = _("""This method allows no signup by users.""")
    uses_requested_state = False

    def get_configuration_fields(self):
        return {
            "no_selfservice_explanation": {
                "formfield": forms.CharField(
                    label=_("Explanation"),
                    required=False,
                ),
                "default": "",
            },
        }

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        raise TypeError(f"{self.__class__} does not support signup")

    @staticmethod
    def signup_is_disabled(method, participant):
        return ParticipationError(
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

    def render_shift_state(self, request):
        return render_basic_participation_pills_shift_state(self, request)
