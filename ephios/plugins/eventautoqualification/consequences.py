import logging
import operator
from collections import Counter

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from ephios.core.consequences import QualificationConsequenceHandler
from ephios.core.models import AbstractParticipation, LocalParticipation
from ephios.plugins.eventautoqualification.models import EventAutoQualificationConfiguration

logger = logging.getLogger(__name__)


@transaction.atomic()
def create_qualification_consequences(sender, **kwargs):
    """
    Creates
    """
    relevant_participations = (
        AbstractParticipation.objects.filter(
            state=AbstractParticipation.States.CONFIRMED,
            shift__end_time__lt=timezone.now(),
            shift__event__auto_qualification_config__isnull=False,
        )
        .filter(~Q(shift__event__auto_qualification_config__handled_for=F("id")))
        .select_related("shift", "shift__event", "shift__event__auto_qualification_config")
    )

    for participation in relevant_participations:
        event = participation.shift.event
        mode = event.auto_qualification_config.mode
        event.auto_qualification_config.handled_for.add(participation)
        # check if the required shift participations exist
        requirements_met = False
        if mode == EventAutoQualificationConfiguration.Modes.ANY_SHIFT:
            requirements_met = True
        elif mode == EventAutoQualificationConfiguration.Modes.LAST_SHIFT:
            requirements_met = (
                participation.shift
                == sorted(event.shifts.all(), key=operator.attrgetter("end_time"))[-1]
            )
        elif mode == EventAutoQualificationConfiguration.Modes.EVERY_SHIFT:
            # count participant hashes in confirmed participations in shifts that are in the past
            participant_hash_counter = Counter(
                hash(participation.participant)
                for participation in AbstractParticipation.objects.filter(
                    state=AbstractParticipation.States.CONFIRMED,
                    shift__event=event,
                    shift__end_time__lt=timezone.now(),
                )
            )
            # if the amount of this participant in confirmed past shifts is equal to the the count of all shifts
            # then this participant attended every shift
            requirements_met = participant_hash_counter[hash(participation.participant)] == len(
                event.shifts.all()
            )

        if requirements_met:
            if not isinstance(participation, LocalParticipation):
                logger.warning(
                    "Cannot create an automatic qualification consequence for non-local participants."
                )
                continue

            user = participation.user

            # skip if extent/refresh only but the user does not have a grant
            if (
                event.auto_qualification_config.extend_only
                and not event.auto_qualification_config.qualification_id
                in user.qualification_grants.values_list("qualification_id", flat=True)
            ):
                continue

            consequence = QualificationConsequenceHandler.create(
                user=user,
                qualification=event.auto_qualification_config.qualification,
                expires=event.auto_qualification_config.expiration_date,
                shift=participation.shift,
            )

            if not event.auto_qualification_config.needs_confirmation:
                consequence.confirm(user=None)
