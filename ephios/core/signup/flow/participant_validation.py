from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ephios.core.dynamic_preferences_registry import GeneralRequiredQualificationPreference
from ephios.core.models import AbstractParticipation, Shift
from ephios.core.signals import participant_signup_checkers
from ephios.core.signup.participants import AbstractParticipant


class BaseSignupError(Exception):
    """Superclass of errors used in the signup mechanism."""

    def __init__(self, message):
        self.message = message


class SignupDisallowedError(BaseSignupError):
    """
    Error to return if the participant cannot sign up.
    """


class ParticipantUnfitError(SignupDisallowedError):
    """
    More specific error to return if the participant cannot
    sign up, because they do not meet the requirements (as per shift structure).
    """


class DeclineDisallowedError(BaseSignupError):
    """Error to return if the participant cannot decline a shift."""


class ActionDisallowedError(SignupDisallowedError, DeclineDisallowedError):
    """Error to return if the participant cannot perform any action on a shift."""


class ImproperlyConfiguredError(ActionDisallowedError):
    """
    Error to return if any signup action cannot be performed
    for technical or configuration reasons.
    """


def check_event_is_active(shift, participant):
    if not shift.event.active:
        return ActionDisallowedError(_("The event is not active."))


def check_participation_state(shift, participant):
    participation = participant.participation_for(shift)
    if participation is not None:
        if (
            participation.state == AbstractParticipation.States.CONFIRMED
            and not shift.signup_flow.configuration.user_can_decline_confirmed
        ):
            raise DeclineDisallowedError(_("You cannot decline by yourself."))
        if participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
            raise ActionDisallowedError(_("You have been rejected."))
        if participation.state == AbstractParticipation.States.USER_DECLINED:
            raise DeclineDisallowedError(_("You have already declined participating."))


def check_inside_signup_timeframe(shift, participant):
    last_time = shift.end_time
    if shift.signup_flow.configuration.signup_until is not None:
        last_time = min(last_time, shift.signup_flow.configuration.signup_until)
    if timezone.now() > last_time:
        raise ActionDisallowedError(_("The signup period is over."))


def check_general_required_qualifications(shift, participant):
    if not participant.has_qualifications(
        shift.event.type.preferences[GeneralRequiredQualificationPreference.name]
    ):
        raise ParticipantUnfitError(
            _(
                "You lack the necessary qualification to participate in {eventtype} type events."
            ).format(eventtype=shift.event.type)
        )


def get_conflicting_participations(
    participant: AbstractParticipant, shift: Shift, start_time=None, end_time=None, total=False
):
    """
    Return a queryset of participations of a participant in conflict with
    a (potential) participation specified by the arguments.

        Parameters:
            participant: AbstractParticipant to check conflict for
            shift: conflicting participations for this shift
            start_time, end_time: specify times other than the default times of `shift`
            total (bool): If True, only return conflicts that can't be
                          resolved by only participating in only part of `shift`.

        Returns:
            a queryset of participations
    """
    start_time = start_time or shift.start_time
    end_time = end_time or shift.end_time
    qs = participant.all_participations().filter(
        ~Q(shift=shift)
        & Q(state=AbstractParticipation.States.CONFIRMED)
        & Q(start_time__lt=end_time, end_time__gt=start_time)
    )
    if total:
        qs = qs.filter(start_time__lte=shift.start_time, end_time__gte=shift.end_time)
    return qs


def check_conflicting_participations(shift, participant):
    start_time, end_time = shift.start_time, shift.end_time
    if participation := participant.participation_for(shift):
        start_time, end_time = participation.start_time, participation.end_time

    # if users can provide individual times, only total conflicts should block signup
    total = getattr(shift.signup_flow.configuration, "user_can_customize_signup_times", False)
    if conflicts := get_conflicting_participations(
        participant=participant,
        shift=shift,
        start_time=start_time,
        end_time=end_time,
        total=total,
    ):
        raise SignupDisallowedError(
            _("You are already confirmed for other shifts at this time: {shifts}.").format(
                shifts=", ".join(str(conflicting_shift) for conflicting_shift in conflicts)
            )
        )


class BaseSignupActionValidator:
    """
    This class is initialized with a participant and a shift.
    It computes whether the participant can perform certain signup actions.
    """

    def get_checkers(self):
        return []

    def __init__(self, shift, participant):
        self.shift = shift
        self.participant = participant
        self.participation = participant.participation_for(shift)

    def _get_errors(self, error_class):
        errors = []
        for checker in self.get_checkers():
            try:
                checker(self.shift, self.participant)
            except error_class as e:
                errors.append(e)
            except BaseSignupError:
                pass  # ignore other signup errors
        return errors

    def get_signup_errors(self):
        """
        Return a list of errors that prevent the participant from signing up.
        """
        return self._get_errors(SignupDisallowedError)

    def get_decline_errors(self):
        """
        Return a list of errors that prevent the participant from declining.
        """
        return self._get_errors(DeclineDisallowedError)

    def get_action_errors(self):
        """
        Return a list of errors that prevent the participant from performing any action.
        """
        return self._get_errors(BaseSignupError)

    def can_sign_up(self):
        """
        Return whether the participant is allowed to perform signup.
        """
        signupable_state = (
            self.participation is None or not self.participation.is_in_positive_state()
        )
        return signupable_state and not self.get_signup_errors()

    def can_decline(self):
        """
        Whether the participant can decline the shift.
        """
        return not self.get_decline_errors()

    def can_customize_signup(self):
        """
        Return whether the participant gets shown the option to customize their participation.
        """
        positive_state = (
            self.participation is not None and self.participation.is_in_positive_state()
        )

        if positive_state:
            # If in a positive state, check that you can decline and then sign up again.
            return self.can_decline() and not self.get_signup_errors()
        return not self.get_signup_errors()


class BasicSignupActionValidator(BaseSignupActionValidator):
    def get_checkers(self):
        signal_checkers = []
        for _, result in participant_signup_checkers.send(None):
            if result:
                signal_checkers.extend(result)
        structure_checkers = self.shift.structure.get_checkers()
        return [
            check_event_is_active,
            check_participation_state,
            check_inside_signup_timeframe,
            check_general_required_qualifications,
            check_conflicting_participations,
            *structure_checkers,
            *signal_checkers,
        ]


class NoSignupSignupActionValidator(BaseSignupActionValidator):
    def get_no_signup_allowed_message(self):
        raise NotImplementedError

    def signup_is_disabled(self, method, participant):
        raise ActionDisallowedError(self.get_no_signup_allowed_message())

    def get_checkers(self):
        return [self.signup_is_disabled]
