from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ephios.core.models import AbstractParticipation
from ephios.plugins.basesignup.signup.common import QualificationMinMaxBaseSignupMethod


class InstantConfirmationSignupMethod(QualificationMinMaxBaseSignupMethod):
    slug = "instant_confirmation"
    verbose_name = _("Instant Confirmation")
    description = _("""This method instantly confirms every signup after it was requested.""")
    uses_requested_state = False
    registration_button_text = pgettext_lazy("signup button text", "Participate")

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        participation.state = AbstractParticipation.States.CONFIRMED
        return participation
