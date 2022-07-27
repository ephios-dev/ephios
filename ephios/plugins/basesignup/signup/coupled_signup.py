from dataclasses import replace

from django import forms
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation, Shift
from ephios.core.signup.methods import ActionDisallowedError, BaseSignupMethod, SignupStats
from ephios.plugins.basesignup.signup.common import RenderParticipationPillsShiftStateMixin


class CoupledSignupMethod(RenderParticipationPillsShiftStateMixin, BaseSignupMethod):
    slug = "coupled"
    verbose_name = _("coupled to another shift")
    description = _("""This method mirrors signup from another shift.""")
    uses_requested_state = True

    @property
    def configuration_form_class(self):
        class ConfigurationForm(super().configuration_form_class):
            leader_shift_id = forms.ModelChoiceField(
                label=_("shift to mirror participation from"),
                required=True,
                queryset=self.event.shifts.exclude(
                    Q(pk__in=[self.shift.id] if self.shift else [])
                    | Q(signup_method_slug=self.slug)  # no chaining/no cycles!
                ),
            )

            @staticmethod
            def format_leader_shift_id(value):
                return str(Shift.objects.get(id=value) if isinstance(value, int) else value)

        return ConfigurationForm

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        raise TypeError(f"{self.__class__} does not support signup")

    @cached_property
    def leader_shift(self):
        if isinstance(self.configuration.leader_shift_id, Shift):
            return self.configuration.leader_shift_id
        try:
            return Shift.objects.get(id=self.configuration.leader_shift_id)
        except Shift.DoesNotExist:
            return None

    @staticmethod
    def signup_is_disabled(method, participant):
        if method.leader_shift:
            return ActionDisallowedError(
                _("Participation is coupled to {}.").format(method.leader_shift)
            )
        # This is red as it requires responsibles to update the shift configuration.
        return ActionDisallowedError(
            mark_safe(
                f'<span class="text-danger">{_("Participation is coupled to another shift, but the leading shift is missing.")}</span>'
            )
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

    def get_signup_stats(self) -> "SignupStats":
        raw_signupstats = super().get_signup_stats()
        return replace(
            SignupStats.ZERO,
            requested_count=raw_signupstats.requested_count,
            confirmed_count=raw_signupstats.confirmed_count,
        )


@receiver(pre_save)
def update_coupled_shifts(sender, instance, **kwargs):
    # make sure sender is a true subclass of AbstractParticipation
    if not issubclass(sender, AbstractParticipation) and sender != AbstractParticipation:
        return

    if instance.state == AbstractParticipation.States.GETTING_DISPATCHED:
        return

    coupled_shifts = [
        shift
        for shift in instance.shift.event.shifts.all()
        if shift.signup_method.slug == CoupledSignupMethod.slug
        and shift.signup_method.leader_shift == instance.shift
    ]

    for coupled_shift in coupled_shifts:
        # make sure a type `instance` exists also for `coupled_shift`
        coupled_participation = coupled_shift.signup_method.get_participation_for(
            instance.participant
        )
        coupled_participation.state = instance.state
        coupled_participation.save()


@receiver(post_save)
def fill_new_shift(sender, instance, **kwargs):
    # make sure sender is a true subclass of AbstractParticipation
    if not issubclass(sender, Shift) or instance.signup_method_slug != CoupledSignupMethod.slug:
        return

    if not (leader_shift := instance.signup_method.leader_shift):
        return

    for leader_participation in leader_shift.participations.exclude(
        state=AbstractParticipation.States.GETTING_DISPATCHED
    ):
        # make sure a type `instance` exists also for `coupled_shift`
        coupled_participation = instance.signup_method.get_participation_for(
            leader_participation.participant
        )
        coupled_participation.state = leader_participation.state
        coupled_participation.save()
