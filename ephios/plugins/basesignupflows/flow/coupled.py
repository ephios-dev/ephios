from django import forms
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext

from ephios.core.models import AbstractParticipation, Shift
from ephios.core.signup.flow.base import BaseSignupFlow
from ephios.core.signup.flow.participant_validation import (
    ActionDisallowedError,
    NoSignupSignupActionValidator,
)
from ephios.core.signup.forms import SignupConfigurationForm


class CoupledSignupActionValidator(NoSignupSignupActionValidator):
    def get_no_signup_allowed_message(self):
        if self.shift.signup_flow.leader_shift:
            return ActionDisallowedError(
                _("Participation is coupled to {}.").format(self.shift.signup_flow.leader_shift)
            )
        # This is red as it requires responsibles to update the shift configuration.
        text = _("Participation is coupled to another shift, but the leading shift is missing.")
        return ActionDisallowedError(mark_safe(f'<span class="text-danger">{text}</span>'))


class CoupledFlowConfigurationForm(SignupConfigurationForm):
    leader_shift_id = forms.ModelChoiceField(
        label=_("shift to mirror participation from"),
        required=True,
        queryset=Shift.objects.none(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        leader_shift_queryset = self.event.shifts.exclude(
            Q(pk__in=[self.shift.id] if self.shift else [])
            | Q(signup_flow_slug=CoupledSignupFlow.slug)  # no chaining/no cycles!
        )
        self.fields["leader_shift_id"].queryset = leader_shift_queryset

    @staticmethod
    def format_leader_shift_id(value):
        try:
            return str(Shift.objects.get(id=value) if isinstance(value, int) else value)
        except Shift.DoesNotExist:
            return pgettext("coupled signup leader shift", "missing")


class CoupledSignupFlow(BaseSignupFlow):
    slug = "coupled"
    verbose_name = _("coupled to another shift")
    description = _("""This method mirrors signup from another shift.""")
    uses_requested_state = True
    signup_action_validator_class = CoupledSignupActionValidator
    configuration_form_class = CoupledFlowConfigurationForm

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


@receiver(pre_save, dispatch_uid="ephios_coupled_signup_update_coupled_shifts")
def update_coupled_shifts(sender, instance, **kwargs):
    # make sure sender is a true subclass of AbstractParticipation
    if not issubclass(sender, AbstractParticipation) or sender == AbstractParticipation:
        return

    if instance.state == AbstractParticipation.States.GETTING_DISPATCHED:
        return

    coupled_shifts = [
        shift
        for shift in instance.shift.event.shifts.all()
        if shift.signup_flow_slug == CoupledSignupFlow.slug
        and shift.signup_flow.leader_shift == instance.shift
    ]

    for coupled_shift in coupled_shifts:
        # make sure a type `instance` exists also for `coupled_shift`
        coupled_participation = coupled_shift.signup_flow.get_or_create_participation_for(
            instance.participant
        )
        coupled_participation.state = instance.state
        coupled_participation.save()


@receiver(post_save, dispatch_uid="ephios_coupled_signup_fill_new_shift")
def fill_new_shift(sender, instance, **kwargs):
    if not issubclass(sender, Shift) or instance.signup_flow_slug != CoupledSignupFlow.slug:
        return

    if not (leader_shift := instance.signup_flow.leader_shift):
        return

    for leader_participation in leader_shift.participations.exclude(
        state=AbstractParticipation.States.GETTING_DISPATCHED
    ):
        # make sure a type `instance` exists also for `coupled_shift`
        coupled_participation = instance.signup_flow.get_or_create_participation_for(
            leader_participation.participant
        )
        coupled_participation.state = leader_participation.state
        coupled_participation.save()
