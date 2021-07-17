from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup import BaseSignupMethod
from ephios.plugins.basesignup.signup.common import (
    MinMaxParticipantsMixin,
    QualificationsRequiredSignupMixin,
)


class InstantConfirmationSignupMethod(
    QualificationsRequiredSignupMixin, MinMaxParticipantsMixin, BaseSignupMethod
):
    slug = "instant_confirmation"
    verbose_name = _("Instant Confirmation")
    description = _("""This method instantly confirms every signup after it was requested.""")
    uses_requested_state = False

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        participation.state = AbstractParticipation.States.CONFIRMED
        return participation
