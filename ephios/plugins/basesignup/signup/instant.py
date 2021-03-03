from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.registries import global_preferences_registry

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

    def perform_signup(self, participant, **kwargs):
        participation = super().perform_signup(participant, **kwargs)
        participation.state = AbstractParticipation.States.CONFIRMED
        participation.save()
        return participation

    def get_participation_display(self):
        relevant_qualification_categories = global_preferences_registry.manager()[
            "general__relevant_qualification_categories"
        ]
        participation_info = [
            [
                f"{participant.first_name} {participant.last_name}",
                ", ".join(
                    participant.qualifications.filter(
                        category__in=relevant_qualification_categories
                    ).values_list("title", flat=True)
                ),
            ]
            for participant in self.shift.get_participants()
        ]
        min_count, max_count = self.get_participant_count_bounds()
        rendered_count = max(min_count or 0, max_count or 0)
        if len(participation_info) < rendered_count:
            required_qualifications = self.configuration.required_qualifications
            qualifications_display = (
                ", ".join(required_qualifications.values_list("title", flat=True))
                if required_qualifications
                else ""
            )
            participation_info += [["", qualifications_display]] * (
                rendered_count - len(participation_info)
            )
        return participation_info
