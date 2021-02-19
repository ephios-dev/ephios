from django import forms
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup import ParticipationError
from ephios.plugins.basesignup.signup.common import SimpleQualificationsRequiredSignupMethod


class InstantConfirmationSignupMethod(SimpleQualificationsRequiredSignupMethod):
    slug = "instant_confirmation"
    verbose_name = _("Instant Confirmation")
    description = _("""This method instantly confirms every signup after it was requested.""")
    uses_requested_state = False

    @property
    def signup_checkers(self):
        return super().signup_checkers + [self.check_maximum_number_of_participants]

    @staticmethod
    def check_maximum_number_of_participants(method, participant):
        if method.configuration.maximum_number_of_participants is not None:
            current_count = AbstractParticipation.objects.filter(
                shift=method.shift, state=AbstractParticipation.States.CONFIRMED
            ).count()
            if current_count >= method.configuration.maximum_number_of_participants:
                return ParticipationError(_("The maximum number of participants is reached."))

    def get_configuration_fields(self):
        return {
            **super().get_configuration_fields(),
            "maximum_number_of_participants": {
                "formfield": forms.IntegerField(min_value=1, required=False),
                "default": None,
                "publish_with_label": _("Maximum number of participants"),
            },
        }

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

    def perform_signup(self, participant, **kwargs):
        participation = super().perform_signup(participant, **kwargs)
        participation.state = AbstractParticipation.States.CONFIRMED
        participation.save()
        return participation
