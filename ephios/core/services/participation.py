import logging

from django.conf import settings
from django.utils import timezone

from ephios.core.models import AbstractParticipation
from ephios.core.services.password_reset import logger

logger = logging.getLogger(__name__)


def send_participation_finished(sender, **kwargs):
    """
    This method is registered in signals.py as a receiver of ``periodic_signal``.
    """
    from ephios.core.signals import participation_finished

    relevant_participations = AbstractParticipation.objects.filter(
        state=AbstractParticipation.States.CONFIRMED,
        shift__end_time__lt=timezone.now(),
        finished=False,
    ).select_related("shift", "shift__event")
    for participation in relevant_participations:
        participation.finished = True
        participation.save()
        for __, result in participation_finished.send_robust(None, participation=participation):
            if isinstance(result, Exception):
                if settings.DEBUG:
                    raise result
                logger.exception(
                    "Error while dispatching participation_finished: %s", exc_info=result
                )
