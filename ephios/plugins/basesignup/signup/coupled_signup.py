from django import forms
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation, Shift
from ephios.core.signup import BaseSignupMethod, ParticipationError
from ephios.plugins.basesignup.signup.common import render_basic_participation_pills_shift_state


class CoupledSignupMethod(BaseSignupMethod):
    slug = "coupled"
    verbose_name = _("coupled to another shift")
    description = _("""This method mirrors signup from another shift.""")
    uses_requested_state = True

    def get_configuration_fields(self):
        return {
            "coupled_shift_id": {
                "formfield": forms.ModelChoiceField(
                    label=_("shift to mirror participation from"),
                    required=True,
                    queryset=self.event.shifts.exclude(  # TODO: you can select the self shift way to often still
                        pk__in=[self.shift.id] if self.shift else [],
                        signup_method_slug=self.slug,  # no chaining/no cycles!
                    ),
                ),
                "default": None,
            },
        }

    @cached_property
    def coupled_shift(self):
        try:
            return Shift.objects.get(id=self.configuration.coupled_shift_id)
        except Shift.DoesNotExist:
            return None

    @staticmethod
    def signup_is_disabled(method, participant):
        if method.coupled_shift:
            return ParticipationError(
                _("Participation is coupled to {}.").format(method.coupled_shift)
            )
        return ParticipationError(_("Participation is coupled to another shift."))

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
        return render_basic_participation_pills_shift_state(
            self, request, {"disposition_url": None}
        )
        # return self.coupled_shift.signup_method.render_shift_state(request)


@receiver(pre_save)
def pre_save_callback(sender, instance, **kwargs):
    # make sure sender is a true subclass of AbstractParticipation
    if not issubclass(sender, AbstractParticipation) and sender != AbstractParticipation:
        return

    coupled_shifts = [
        shift
        for shift in instance.shift.event.shifts.all()
        if shift.signup_method.slug == CoupledSignupMethod.slug and shift != instance.shift
    ]

    for coupled_shift in coupled_shifts:
        # make sure a type `instance` exists also for `coupled_shift`
        coupled_participation = coupled_shift.signup_method.get_participation_for(
            instance.participant
        )
        coupled_participation.state = instance.state
        coupled_participation.save()

        # TODO move this somewhere better
        coupled_shift.participations.filter(
            state=AbstractParticipation.States.GETTING_DISPATCHED
        ).non_polymorphic().delete()
