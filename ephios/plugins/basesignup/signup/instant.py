from django.template.loader import get_template
from django.urls import reverse
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

    def render_shift_state(self, request):
        return get_template("basesignup/instant/fragment_state.html").render(
            {
                "shift": self.shift,
                "disposition_url": (
                    reverse("core:shift_disposition", kwargs=dict(pk=self.shift.pk))
                    if request.user.has_perm("core.change_event", obj=self.shift.event)
                    else None
                ),
            }
        )

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        participation.state = AbstractParticipation.States.CONFIRMED
        return participation
