import logging
import operator
from collections import Counter

from django.db.models import Q

from ephios.core.consequences import QualificationConsequenceHandler
from ephios.core.models import AbstractParticipation, LocalParticipation
from ephios.plugins.eventautoqualification.models import EventAutoQualificationConfiguration

logger = logging.getLogger(__name__)


def create_qualification_consequence(sender, participation, **kwargs):
    event = participation.shift.event
    try:
        mode = event.auto_qualification_config.mode
    except EventAutoQualificationConfiguration.DoesNotExist:
        return

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
        # count participant hashes in finished participations (and this one)
        participant_hash_counter = Counter(
            hash(participation.participant)
            for participation in AbstractParticipation.objects.filter(
                Q(finished=True) | Q(id=participation.id)
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
            return

        user = participation.user

        # skip if extent/refresh only but the user does not have a grant
        if (
            event.auto_qualification_config.extend_only
            and not event.auto_qualification_config.qualification_id
            in user.qualification_grants.values_list("qualification_id", flat=True)
        ):
            return

        consequence = QualificationConsequenceHandler.create(
            user=user,
            qualification=event.auto_qualification_config.qualification,
            expires=event.auto_qualification_config.expiration_date,
            shift=participation.shift,
        )

        if not event.auto_qualification_config.needs_confirmation:
            consequence.confirm(user=None)
