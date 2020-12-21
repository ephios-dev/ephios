from django.dispatch import receiver

from ephios.user_management.consequences import (
    QualificationConsequenceHandler,
    WorkingHoursConsequenceHandler,
    register_consequence_handlers,
)


@receiver(
    register_consequence_handlers,
    dispatch_uid="ephios.user_management.signals.register_base_consequence_handlers",
)
def register_base_consequence_handlers(sender, **kwargs):
    return [WorkingHoursConsequenceHandler, QualificationConsequenceHandler]
