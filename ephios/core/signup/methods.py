import functools
import logging
from abc import ABC
from argparse import Namespace
from collections import OrderedDict
from typing import List

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ephios.core.dynamic_preferences_registry import GeneralRequiredQualificationPreference
from ephios.core.models import AbstractParticipation, Shift
from ephios.core.services.notifications.types import (
    ResponsibleConfirmedParticipationDeclinedNotification,
)
from ephios.core.signals import check_participant_signup, register_signup_methods
from ephios.core.signup.participants import AbstractParticipant
from ephios.core.signup.stats import SignupStats
from ephios.extra.utils import format_anything

logger = logging.getLogger(__name__)


def installed_signup_methods():
    for _, methods in register_signup_methods.send_to_all_plugins(None):
        yield from methods


def enabled_signup_methods():
    for _, methods in register_signup_methods.send(None):
        yield from methods


def signup_method_from_slug(slug, shift=None, event=None):
    for method in installed_signup_methods():
        if method.slug == slug:
            return method(shift, event=event)
    raise ValueError(_("Signup Method '{slug}' was not found.").format(slug=slug))


class ParticipationError(ValidationError):
    """Superclass of errors used in the signup mechanism."""


class ActionDisallowedError(ValidationError):
    """Error to return if the participant cannot perform an action on a shift."""


class SignupDisallowedError(ActionDisallowedError):
    """
    Error to return if the participant cannot sign up for a shift,
    even if formally fit, because of certain other circumstances.
    """


class DeclineDisallowedError(ActionDisallowedError):
    """Error to return if the participant cannot decline a shift."""


class ParticipantUnfitError(ParticipationError):
    """
    Error to return if the participant is unfit for a shift,
    regardless of participation state or situation.
    """


class ImproperlyConfiguredError(ParticipationError):
    """
    Error to return if signup cannot be performed for
    technical or configuration reasons.
    """


def check_event_is_active(method, participant):
    if not method.shift.event.active:
        return ActionDisallowedError(_("The event is not active."))


def check_participation_state_for_signup(method, participant):
    participation = participant.participation_for(method.shift)
    if participation is not None:
        if participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
            return SignupDisallowedError(_("You have been rejected."))


def check_participation_state_for_decline(method, participant):
    participation = participant.participation_for(method.shift)
    if participation is not None:
        if (
            participation.state == AbstractParticipation.States.CONFIRMED
            and not method.configuration.user_can_decline_confirmed
        ):
            return DeclineDisallowedError(_("You cannot decline by yourself."))
        if participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
            return DeclineDisallowedError(_("You have been rejected."))
        if participation.state == AbstractParticipation.States.USER_DECLINED:
            return DeclineDisallowedError(_("You have already declined participating."))


def check_inside_signup_timeframe(method, participant):
    last_time = method.shift.end_time
    if method.configuration.signup_until is not None:
        last_time = min(last_time, method.configuration.signup_until)
    if timezone.now() > last_time:
        return ActionDisallowedError(_("The signup period is over."))


def check_participant_age(method, participant):
    minimum_age = getattr(method.configuration, "minimum_age", None)
    day = method.shift.start_time.date()
    age = participant.get_age(day)
    if minimum_age is not None and age is not None and age < minimum_age:
        return ParticipantUnfitError(
            _("You are too young. The minimum age is {age}.").format(age=minimum_age)
        )


def check_general_required_qualifications(method, participant):
    if not participant.has_qualifications(
        method.shift.event.type.preferences[GeneralRequiredQualificationPreference.name]
    ):
        return ParticipantUnfitError(
            _(
                "You lack the necessary qualification to participate in {eventtype} type events."
            ).format(eventtype=method.shift.event.type)
        )


def check_participant_signup_signal(method, participant):
    errors = []
    for _, result in check_participant_signup.send(None, method=method, participant=participant):
        if result is not None:
            errors.append(result)
    return errors


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


def check_conflicting_participations(method, participant):
    start_time, end_time = method.shift.start_time, method.shift.end_time
    if participation := participant.participation_for(method.shift):
        start_time, end_time = participation.start_time, participation.end_time

    # if users can provide individual times, only total conflicts should block signup
    total = getattr(method.configuration, "user_can_customize_signup_times", False)
    if conflicts := get_conflicting_participations(
        participant=participant,
        shift=method.shift,
        start_time=start_time,
        end_time=end_time,
        total=total,
    ):
        return SignupDisallowedError(
            _("You are already confirmed for other shifts at this time: {shifts}.").format(
                shifts=", ".join(str(shift) for shift in conflicts)
            )
        )


class AbstractSignupMethod(ABC):
    # pylint: disable=too-many-public-methods

    """
    Abstract base class for signup methods.

    A signup method is a way to sign up for a shift.
    It combines logic for checking whether a participant can sign up for a shift,
    and creating participations.

    It also provides views for signing up using the web interface and forms for
    disposition and configuration.
    """

    def __init__(self, shift, event=None):
        self.shift = shift
        self.event = getattr(shift, "event", event)

    @property
    def slug(self):
        """
        A unique identifier for this signup method.
        """
        raise NotImplementedError()

    @property
    def verbose_name(self):
        """
        The human-readable name of this signup method.
        """
        raise NotImplementedError()

    @property
    def description(self):
        """
        A human-readable description of this signup method.
        """
        raise NotImplementedError()

    @property
    def disposition_participation_form_class(self):
        """
        This form will be used for participations in disposition.
        Set to None if you don't want to support the default disposition.
        """
        raise NotImplementedError()

    @property
    def signup_view(self):
        """
        This view will be used to sign up for shifts.
        """
        raise NotImplementedError()

    def get_configuration_form(self):
        """
        This form will be used to configure this signup method.
        The cleaned data will be saved to shift.signup_configuration
        """
        raise NotImplementedError()

    def render(self, context):
        """
        Render the state/participations of the shift.
        Match the signature of template.render for use with the include template tag:
        {% include shift.signup_method %}
        By default, this loads `shift_state_template_name` and renders it using context from `get_shift_state_context_data`.
        """
        raise NotImplementedError()

    @property
    def registration_button_text(self):
        """
        The text of the registration button.
        """
        return _("Sign up")

    @property
    def uses_requested_state(self):
        """
        Whether this signup method uses the requested state.
        """
        return True

    def get_signup_errors(self, participant) -> List[ParticipationError]:
        """Return a list of ParticipationErrors that describe reasons for not being able to sign up."""
        raise NotImplementedError()

    def get_decline_errors(self, participant) -> List[ParticipationError]:
        """Return a list of ParticipationErrors that describe reasons for not being able to decline."""
        raise NotImplementedError()

    def can_decline(self, participant):
        """
        Return whether the participant is allowed to decline.
        """
        return not self.get_decline_errors(participant)

    def can_sign_up(self, participant):
        """
        Return whether the participant is allowed to perform signup.
        """
        signupable_state = (
            p := participant.participation_for(self.shift)
        ) is None or not p.is_in_positive_state()
        return signupable_state and not self.get_signup_errors(participant)

    def can_customize_signup(self, participant):
        """
        Return whether the participant gets shown the option to customize their participation.
        """
        positive_state = (
            p := participant.participation_for(self.shift)
        ) is not None and p.is_in_positive_state()

        if positive_state:
            # If in a positive state, check that you can decline and then sign up again.
            return self.can_decline(participant) and not self.get_signup_errors(participant)
        return not self.get_signup_errors(participant)

    def has_customized_signup(self, participation):
        """
        Return whether the participation was customized in a way specific to this signup method.
        """
        # This method should most likely check the participation's data attribute for modifications it has done.
        # 'customized' in this context means that the dispositioning person should give special attention to this participation.
        return False

    def get_or_create_participation_for(self, participant) -> AbstractParticipation:
        return participant.participation_for(self.shift) or participant.new_participation(
            self.shift
        )

    def perform_signup(
        self, participant: AbstractParticipant, participation=None, **kwargs
    ) -> AbstractParticipation:
        """
        Perform the signup for the given participant.
        kwargs are passed from the signup view and can be used to customize the signup.
        Usually it's the cleaned_data from the signup form.
        """
        raise NotImplementedError()

    def perform_decline(self, participant, participation=None, **kwargs):
        """
        Perform the decline for the given participant.
        """
        raise NotImplementedError()

    def get_signup_info(self):
        """Return key/value pairs about the configuration to show in exports etc."""
        # TODO maybe move this to an exporter class?
        raise NotImplementedError()

    def get_participation_display(self):
        # TODO move to exporter class?
        raise NotImplementedError()

    def get_participant_count_bounds(self):
        """
        Return a typle of min, max for how many participants are allowed for the shift.
        Use None for any value if it is not specifiable."""
        raise NotImplementedError()

    def get_signup_stats(self) -> "SignupStats":
        """
        Return an instance of SignupStats for the shift.
        """
        raise NotImplementedError()


class BaseSignupMethod(AbstractSignupMethod):
    # pylint: disable=too-many-public-methods

    @property
    def disposition_participation_form_class(self):
        from .disposition import BaseDispositionParticipationForm

        return BaseDispositionParticipationForm

    @property
    def configuration_form_class(self):
        from ephios.core.signup.forms import BaseSignupMethodConfigurationForm

        return BaseSignupMethodConfigurationForm

    @property
    def signup_view_class(self):
        from ephios.core.signup.views import BaseSignupView

        return BaseSignupView

    @property
    def shift_state_template_name(self):
        raise NotImplementedError

    @property
    def signup_view(self):
        return self.signup_view_class.as_view(method=self, shift=self.shift)

    @property
    def _signup_checkers(self):
        """Return a list of methods that check if the participant can sign up for the shift."""
        return [
            check_event_is_active,
            check_participation_state_for_signup,
            check_inside_signup_timeframe,
            check_conflicting_participations,
            check_participant_age,
            check_general_required_qualifications,
            check_participant_signup_signal,
        ]

    @property
    def _decline_checkers(self):
        """Return a list of methods that check if the participant can decline the shift."""
        return [
            check_event_is_active,
            check_participation_state_for_decline,
            check_inside_signup_timeframe,
        ]

    def _run_checkers(self, participant, checkers) -> List[ParticipationError]:
        errors = []
        for checker in checkers:
            # checkers can return None, a single ParticipationError, or a list of them
            if (error := checker(self, participant)) is not None:
                if isinstance(error, list):
                    errors.extend(error)
                else:
                    errors.append(error)
        return errors

    @functools.lru_cache(maxsize=200)
    def get_signup_errors(self, participant) -> List[ParticipationError]:
        """Return a list of ParticipationErrors that describe reasons for not being able to sign up."""
        return self._run_checkers(participant, self._signup_checkers)

    @functools.lru_cache(maxsize=200)
    def get_decline_errors(self, participant):
        """Return a list of ParticipationErrors that describe reasons for not being able to decline."""
        return self._run_checkers(participant, self._decline_checkers)

    def perform_signup(
        self, participant: AbstractParticipant, participation=None, **kwargs
    ) -> AbstractParticipation:
        """
        Creates and/or configures a participation object for a given participant and sends out notifications.
        Passes the participation and kwargs to configure_participation to do configuration specific to the signup method.
        """
        from ephios.core.services.notifications.types import (
            ResponsibleParticipationRequestedNotification,
        )

        if errors := self.get_signup_errors(participant):
            raise ParticipationError(errors)
        participation = participation or self.get_or_create_participation_for(participant)
        participation = self._configure_participation(participation, **kwargs)
        participation.save()
        ResponsibleParticipationRequestedNotification.send(participation)
        return participation

    def perform_decline(self, participant, participation=None, **kwargs):
        """Create and configure a declining participation object for the given participant. `kwargs` may contain further instructions from a e.g. a form."""
        if errors := self.get_decline_errors(participant):
            raise ParticipationError(errors)
        participation = participation or self.get_or_create_participation_for(participant)
        participation.state = AbstractParticipation.States.USER_DECLINED
        participation.save()
        ResponsibleConfirmedParticipationDeclinedNotification.send(participation)
        return participation

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        """
        Configure the given participation object for signup according to the method's configuration.
        You need at least to set the participations state, as that is not done with the participation form.
        `kwargs` contains the signup form's cleaned_data.
        """
        raise NotImplementedError

    def get_signup_info(self):
        """
        Return key/value pairs about the configuration to show in exports etc.
        """
        form_class = self.configuration_form_class
        return OrderedDict(
            {
                label: getattr(form_class, f"format_{name}", format_anything)(value)
                for name, field in form_class.base_fields.items()
                if (label := field.label) and (value := getattr(self.configuration, name))
            }
        )

    def get_participant_count_bounds(self):
        """
        Return a typle of min, max for how many participants are allowed for the shift.
        Use None for any value if it is not specifiable.
        The default implementation returns None, None to signify both values are not specified.
        """
        return None, None

    def get_signup_stats(self) -> "SignupStats":
        """
        Return an instance of SignupStats for the shift.
        """
        min_count, max_count = self.get_participant_count_bounds()
        participations = list(self.shift.participations.all())
        confirmed_count = sum(
            p.state == AbstractParticipation.States.CONFIRMED for p in participations
        )
        return SignupStats(
            requested_count=sum(
                p.state == AbstractParticipation.States.REQUESTED for p in participations
            ),
            confirmed_count=confirmed_count,
            missing=max(min_count - confirmed_count, 0) if min_count else 0,
            free=max(max_count - confirmed_count, 0) if max_count else None,
            min_count=min_count,
            max_count=max_count,
        )

    def render(self, context):
        try:
            with context.update(self.get_shift_state_context_data(context.request)):
                return get_template(self.shift_state_template_name).template.render(context)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Shift #{self.shift.pk} state render failed")
            with context.update({"exception_message": getattr(e, "message", None)}):
                return get_template("core/fragments/signup_method_missing.html").template.render(
                    context
                )

    def get_shift_state_context_data(self, request, **kwargs):
        """
        Additionally to the context of the event detail view, provide context for rendering `shift_state_template_name`.
        """
        kwargs["shift"] = self.shift
        kwargs["participations"] = self.shift.participations.filter(
            state__in={
                AbstractParticipation.States.REQUESTED,
                AbstractParticipation.States.CONFIRMED,
            }
        ).order_by("-state")
        if self.disposition_participation_form_class is not None:
            kwargs["disposition_url"] = (
                reverse("core:shift_disposition", kwargs={"pk": self.shift.pk})
                if request.user.has_perm("core.change_event", obj=self.shift.event)
                else None
            )
        return kwargs

    def get_participation_display(self):
        """
        Returns a displayable representation of participation that can be rendered into a table (e.g. for pdf export).
        Must return a list of participations or empty slots. Each element of the list has to be a list of a fixed
        size where each entry is rendered to a separate column.
        Ex.: [["participant1_name", "participant1_qualification"], ["participant2_name", "participant2_qualification"]]
        """
        return [
            [f"{participant.first_name} {participant.last_name}"]
            for participant in self.shift.get_participants()
        ]

    def get_configuration_form(self, *args, **kwargs):
        if self.shift is not None:
            kwargs.setdefault("initial", self.configuration.__dict__)
        if self.event is not None:
            kwargs.setdefault("event", self.event)
        form = self.configuration_form_class(*args, **kwargs)
        return form

    def __init__(self, shift, event=None):
        super().__init__(shift, event)
        self.configuration = Namespace(
            **{
                name: field.initial
                for name, field in self.configuration_form_class.base_fields.items()
            }
        )
        if shift is not None:
            for key, value in shift.signup_configuration.items():
                setattr(self.configuration, key, value)
