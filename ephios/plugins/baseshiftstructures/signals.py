from django.dispatch import receiver

from ephios.core.signals import register_shift_structures
from ephios.plugins.baseshiftstructures.structure.groups import (
    NamedGroupsShiftStructure,
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
        NamedGroupsShiftStructure,
    ]
