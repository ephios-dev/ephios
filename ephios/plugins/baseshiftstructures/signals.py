from django.dispatch import receiver

from ephios.core.models.events import AbstractParticipation, Shift
from ephios.core.signals import register_shift_structures, signup_formfields, signup_save
from ephios.core.signup.participants import AbstractParticipant
from ephios.plugins.baseshiftstructures.structure.named_teams import NamedTeamsShiftStructure
from ephios.plugins.baseshiftstructures.structure.qualification_mix import (
    QualificationMixShiftStructure,
)
from ephios.plugins.baseshiftstructures.structure.uniform import UniformShiftStructure


@receiver(
    register_shift_structures,
    dispatch_uid="ephios.plugins.baseshiftstructure.signals.register_base_shift_structures",
)
def register_base_shift_structures(sender, **kwargs):
    return [
        UniformShiftStructure,
        QualificationMixShiftStructure,
        NamedTeamsShiftStructure,
    ]


@receiver(
    signup_formfields, dispatch_uid="ephios.plugins.baseshiftstructure.signals.signup_formfields"
)
def provide_signup_formfields(
    sender,
    shift: Shift,
    participant: AbstractParticipant,
    participation: AbstractParticipation,
    signup_choice,
    **kwargs
):
    return shift.structure.get_signup_formfields(shift, participant, participation, signup_choice)


@receiver(signup_save, dispatch_uid="ephios.plugins.baseshiftstructure.signals.signup_save")
def save_signup(
    sender,
    shift: Shift,
    participant: AbstractParticipant,
    participation: AbstractParticipation,
    cleaned_data,
    **kwargs
):
    shift.structure.save_signup(shift, participant, participation, cleaned_data)
