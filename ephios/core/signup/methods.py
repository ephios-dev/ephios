import dataclasses
import functools
import logging
from argparse import Namespace
from collections import OrderedDict
from datetime import date
from typing import List, Optional

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.shortcuts import redirect
from django.template import Context, Template
from django.template.defaultfilters import yesno
from django.urls import reverse
from django.utils import formats, timezone
from django.utils.functional import SimpleLazyObject, cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views import View

from ephios.core.models import AbstractParticipation, LocalParticipation, Qualification, Shift
from ephios.extra.widgets import CustomSplitDateTimeWidget

from ..signals import participant_from_request, register_signup_methods
from .disposition import BaseDispositionParticipationForm

logger = logging.getLogger(__name__)


def installed_signup_methods():
    for _, methods in register_signup_methods.send_to_all_plugins(None):
        yield from methods


def enabled_signup_methods():
    for _, methods in register_signup_methods.send(None):
        yield from methods


def signup_method_from_slug(slug, shift=None):
    for method in installed_signup_methods():
        if method.slug == slug:
            return method(shift)
    raise ValueError(_("Signup Method '{slug}' was not found.").format(slug=slug))


@dataclasses.dataclass(frozen=True)
class AbstractParticipant:
    first_name: str
    last_name: str
    qualifications: QuerySet = dataclasses.field(hash=False)
    date_of_birth: date
    email: Optional[str]  # if set to None, no notifications are sent

    def get_age(self, today: date = None):
        today, born = today or date.today(), self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def new_participation(self, shift):
        raise NotImplementedError

    def participation_for(self, shift):
        """Return the participation object for a shift. Return None if it does not exist."""
        raise NotImplementedError

    def all_participations(self):
        """Return all participations for this participant"""
        raise NotImplementedError

    @functools.lru_cache
    def collect_all_qualifications(self) -> set:
        """We collect using breadth first search with one query for every layer of inclusion."""
        all_qualifications = set(self.qualifications)
        current = self.qualifications
        while current:
            new = (
                Qualification.objects.filter(included_by__in=current)
                .exclude(id__in=(q.id for q in all_qualifications))
                .distinct()
            )
            all_qualifications |= set(new)
            current = new
        return all_qualifications

    def has_qualifications(self, qualifications):
        return set(qualifications) <= self.collect_all_qualifications()

    def reverse_signup_action(self, shift):
        raise NotImplementedError

    def reverse_event_detail(self, event):
        raise NotImplementedError

    @property
    def icon(self):
        return mark_safe('<span class="fa fa-user"></span>')


@dataclasses.dataclass(frozen=True)
class LocalUserParticipant(AbstractParticipant):
    user: get_user_model()

    def new_participation(self, shift):
        return LocalParticipation(shift=shift, user=self.user)

    def participation_for(self, shift):
        try:
            return LocalParticipation.objects.get(shift=shift, user=self.user)
        except LocalParticipation.DoesNotExist:
            return None

    def all_participations(self):
        return LocalParticipation.objects.filter(user=self.user)

    def reverse_signup_action(self, shift):
        return reverse("core:signup_action", kwargs=dict(pk=shift.pk))

    def reverse_event_detail(self, event):
        return event.get_absolute_url()


class ParticipationError(ValidationError):
    pass


def prevent_getting_participant_from_request_user(request):
    original_user = request.user

    class ProtectedUser(SimpleLazyObject):
        def as_participant(self):
            raise Exception("Access of request.user.as_participant in SignupViews is not allowed.")

    request.user = ProtectedUser(lambda: original_user)


def get_nonlocal_participant_from_session(request):
    for _, participant in participant_from_request.send(sender=None, request=request):
        if participant is not None:
            return participant
    raise PermissionDenied


class BaseSignupView(View):
    """
    This View reacts to the signup or decline buttons being pressed using a POST request.
    It can be modified to not directly create a participation, but show a form first, then
    create the participation.

    Beware that request.user might be anonymous. You should only act on participants acquired
    using `get_participant`.
    """

    shift: Shift = ...
    method: "BaseSignupMethod" = ...

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.participant: AbstractParticipant = kwargs["participant"]
        prevent_getting_participant_from_request_user(request)

    def dispatch(self, request, *args, **kwargs):
        if (choice := request.POST.get("signup_choice")) is not None:
            if choice == "sign_up":
                return self.signup_pressed()
            if choice == "decline":
                return self.decline_pressed()
            raise ValueError(_("'{choice}' is not a valid signup action.").format(choice=choice))
        return super().dispatch(request, *args, **kwargs)

    def signup_pressed(self, **signup_kwargs):
        try:
            with transaction.atomic():
                self.method.perform_signup(self.participant, **signup_kwargs)
                messages.success(
                    self.request,
                    self.method.signup_success_message.format(shift=self.shift),
                )
        except ParticipationError as errors:
            for error in errors:
                messages.error(self.request, self.method.signup_error_message.format(error=error))
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def decline_pressed(self, **decline_kwargs):
        try:
            with transaction.atomic():
                self.method.perform_decline(self.participant, **decline_kwargs)
                messages.info(
                    self.request, self.method.decline_success_message.format(shift=self.shift)
                )
        except ParticipationError as errors:
            for error in errors:
                messages.error(self.request, self.method.decline_error_message.format(error=error))
        return redirect(self.participant.reverse_event_detail(self.shift.event))


def check_event_is_active(method, participant):
    if not method.shift.event.active:
        return ParticipationError(_("The event is not active."))


def check_participation_state_for_signup(method, participant):
    participation = participant.participation_for(method.shift)
    if participation is not None:
        if participation.state == AbstractParticipation.States.REQUESTED:
            return ParticipationError(
                _("You have already requested your participation for {shift}").format(
                    shift=method.shift
                )
            )
        if participation.state == AbstractParticipation.States.CONFIRMED:
            return ParticipationError(
                _("You are already signed up for {shift}.").format(shift=method.shift)
            )
        if participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
            return ParticipationError(
                _("You are rejected from {shift}.").format(shift=method.shift)
            )


def check_participation_state_for_decline(method, participant):
    participation = participant.participation_for(method.shift)
    if participation is not None:
        if (
            participation.state == AbstractParticipation.States.CONFIRMED
            and not method.configuration.user_can_decline_confirmed
        ):
            return ParticipationError(
                _("You are bindingly signed up for {shift}.").format(shift=method.shift)
            )
        if participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
            return ParticipationError(
                _("You are rejected from {shift}.").format(shift=method.shift)
            )
        if participation.state == AbstractParticipation.States.USER_DECLINED:
            return ParticipationError(
                _("You have already declined participating in {shift}.").format(shift=method.shift)
            )


def check_inside_signup_timeframe(method, participant):
    last_time = method.shift.end_time
    if method.configuration.signup_until is not None:
        last_time = min(last_time, method.configuration.signup_until)
    if timezone.now() > last_time:
        return ParticipationError(_("The signup period is over."))


def check_participant_age(method, participant):
    minimum_age = method.configuration.minimum_age
    day = method.shift.start_time.date()
    if minimum_age is not None and participant.get_age(day) < minimum_age:
        return ParticipationError(
            _("You are too young. The minimum age is {age}.").format(age=minimum_age)
        )


def get_conflicting_participations(shift, participant):
    return participant.all_participations().filter(
        ~Q(shift=shift)
        & Q(state=AbstractParticipation.States.CONFIRMED)
        & Q(shift__start_time__lt=shift.end_time, shift__end_time__gt=shift.start_time)
    )


def check_conflicting_shifts(method, participant):
    if get_conflicting_participations(method.shift, participant).exists():
        return ParticipationError(_("You are already confirmed for another shift at this time."))


class BaseSignupMethod:
    # pylint: disable=too-many-public-methods

    @property
    def slug(self):
        raise NotImplementedError()

    @property
    def verbose_name(self):
        raise NotImplementedError()

    @property
    def disposition_participation_form_class(self):
        """
        This form will be used for participations in disposition.
        Set to None if you don't want to support the default disposition.
        """
        return BaseDispositionParticipationForm

    @property
    def configuration_form_class(self):
        return forms.Form

    @property
    def signup_view_class(self):
        return BaseSignupView

    description = """"""

    # use _ == gettext_lazy!
    registration_button_text = _("Sign up")
    signup_success_message = _("You have successfully signed up for {shift}.")
    signup_error_message = _("Signing up failed: {error}")
    decline_success_message = _("You have successfully declined {shift}.")
    decline_error_message = _("Declining failed: {error}")

    uses_requested_state = True

    def __init__(self, shift):
        self.shift = shift
        self.configuration = Namespace(
            **{name: config["default"] for name, config in self.get_configuration_fields().items()}
        )
        if shift is not None:
            for key, value in shift.signup_configuration.items():
                setattr(self.configuration, key, value)

    @cached_property
    def signup_view(self):
        return self.signup_view_class.as_view(method=self, shift=self.shift)

    @property
    def _signup_checkers(self):
        return [
            check_event_is_active,
            check_participation_state_for_signup,
            check_inside_signup_timeframe,
            check_participant_age,
            check_conflicting_shifts,
        ]

    @property
    def _decline_checkers(self):
        return [
            check_event_is_active,
            check_participation_state_for_decline,
            check_inside_signup_timeframe,
        ]

    @functools.lru_cache()
    def get_signup_errors(self, participant) -> List[ParticipationError]:
        return [
            error
            for checker in self._signup_checkers
            if (error := checker(self, participant)) is not None
        ]

    @functools.lru_cache()
    def get_decline_errors(self, participant):
        return [
            error
            for checker in self._decline_checkers
            if (error := checker(self, participant)) is not None
        ]

    def can_decline(self, participant):
        return not self.get_decline_errors(participant)

    def can_sign_up(self, participant):
        return not self.get_signup_errors(participant)

    def get_participation_for(self, participant):
        return participant.participation_for(self.shift) or participant.new_participation(
            self.shift
        )

    def perform_signup(self, participant: AbstractParticipant, **kwargs) -> AbstractParticipation:
        """
        Creates and/or configures a participation object for a given participant and sends out notifications.
        Passes the participation and kwargs to configure_participation to do configuration specific to the signup method
        """
        from ephios.core.services.notifications.types import ResponsibleParticipationRequested

        if errors := self.get_signup_errors(participant):
            raise ParticipationError(errors)
        participation = self._configure_participation(
            self.get_participation_for(participant), **kwargs
        )
        participation.save()
        ResponsibleParticipationRequested.send(participation)
        return participation

    def perform_decline(self, participant, **kwargs):
        """Create and configure a declining participation object for the given participant. `kwargs` may contain further instructions from a e.g. a form."""
        if errors := self.get_decline_errors(participant):
            raise ParticipationError(errors)
        participation = self.get_participation_for(participant)
        participation.state = AbstractParticipation.States.USER_DECLINED
        participation.save()
        return participation

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        """
        Configure the given participation object for signup according to the method's configuration.
        You need at least to set the participations state. `kwargs` may contain further instructions from e.g. a form.
        """
        return NotImplemented

    def get_configuration_fields(self):
        return OrderedDict(
            {
                "minimum_age": {
                    "formfield": forms.IntegerField(required=False, min_value=1, max_value=999),
                    "default": 16,
                    "publish_with_label": _("Minimum age"),
                },
                "signup_until": {
                    "formfield": forms.SplitDateTimeField(
                        required=False, widget=CustomSplitDateTimeWidget
                    ),
                    "default": None,
                    "publish_with_label": _("Signup until"),
                    "format": functools.partial(
                        formats.date_format, format="SHORT_DATETIME_FORMAT"
                    ),
                },
                "user_can_decline_confirmed": {
                    "formfield": forms.BooleanField(
                        label=_("Confirmed users can decline by themselves"),
                        required=False,
                        help_text=_("only if the signup timeframe has not ended"),
                    ),
                    "default": False,
                    "publish_with_label": _("Can decline after confirmation"),
                    "format": yesno,
                },
            }
        )

    def get_signup_info(self):
        """
        Return key/value pairs about the configuration to show in the shift info box.
        """
        fields = self.get_configuration_fields()
        return OrderedDict(
            {
                label: field.get("format", str)(value)
                for key, field in fields.items()
                if (label := field.get("publish_with_label", False))
                and (value := getattr(self.configuration, key))
            }
        )

    def get_participant_count_bounds(self):
        """
        Return a typle of min, max for how many participants are allowed for the shift.
        Use None for any value if it is not specifiable.
        The default implementation returns None, None to signify both values are not specified.
        """
        return None, None

    def get_signup_stats(self):
        """
        Return an instance of SignupStats for the shift.
        """
        min_count, max_count = self.get_participant_count_bounds()
        participations = list(self.shift.participations.all())
        return SignupStats(
            requested_count=sum(
                p.state == AbstractParticipation.States.REQUESTED for p in participations
            ),
            signed_up_count=sum(
                p.state == AbstractParticipation.States.CONFIRMED for p in participations
            ),
            min_count=min_count,
            max_count=max_count,
        )

    def render_shift_state(self, request):
        """
        Render html that will be shown in the shift info box.
        Use it to inform about the current state of the shift and participations.
        """
        return ""

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
        form = self.configuration_form_class(*args, **kwargs)
        for name, config in self.get_configuration_fields().items():
            form.fields[name] = config["formfield"]
        return form

    def render_configuration_form(self, *args, form=None, **kwargs):
        form = form or self.get_configuration_form(*args, **kwargs)
        template = Template(
            template_string="{% load crispy_forms_filters %}{{ form|crispy }}"
        ).render(Context({"form": form}))
        return template


@dataclasses.dataclass()
class SignupStats:
    requested_count: int
    signed_up_count: int
    min_count: Optional[int]
    max_count: Optional[int]

    def __add__(self, other: "SignupStats"):
        if self.min_count is not None or other.min_count is not None:
            min_count = (self.min_count or 0) + (other.min_count or 0)
        else:
            min_count = None
        if self.max_count is not None and other.max_count is not None:
            max_count = (self.max_count or 0) + (other.max_count or 0)
        else:
            max_count = None
        return SignupStats(
            requested_count=self.requested_count + other.requested_count,
            signed_up_count=self.signed_up_count + other.signed_up_count,
            min_count=min_count,
            max_count=max_count,
        )
