from django import forms
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup import BaseSignupMethod, ParticipationError


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
                    required=True,
                ),
                "default": _("Signup for this shift is disabled."),
            },
        }

    @staticmethod
    def signup_is_disabled(method, participant):
        return ParticipationError(method.configuration.no_selfservice_explanation)

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
        participations = self.shift.participations.filter(
            state__in={
                AbstractParticipation.States.REQUESTED,
                AbstractParticipation.States.CONFIRMED,
            }
        ).order_by("-state")
        return get_template("basesignup/fragment_state_common.html").render(
            {
                "shift": self.shift,
                "participations": participations,
                "disposition_url": (
                    reverse("core:shift_disposition", kwargs=dict(pk=self.shift.pk))
                    if request.user.has_perm("core.change_event", obj=self.shift.event)
                    else None
                ),
            }
        )
