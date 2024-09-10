from django.dispatch import receiver

from ephios.core.signals import register_shift_structures
from ephios.plugins.complexsignup.structure import ComplexShiftStructure


@receiver(
    register_shift_structures,
    dispatch_uid="ephios.plugins.complexsignup.signals.register_complex_shift_structures",
)
def register_complex_shift_structures(sender, **kwargs):
    return [
        ComplexShiftStructure,
    ]
