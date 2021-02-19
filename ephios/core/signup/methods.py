import functools
from argparse import Namespace
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

import django.dispatch
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import redirect
from django.template import Context, Template
from django.template.defaultfilters import yesno
from django.utils import formats, timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View

from ephios.core.models import AbstractParticipation, LocalParticipation, Qualification, Shift
from ephios.extra.widgets import CustomSplitDateTimeWidget

from .disposition import BaseDispositionParticipationForm

register_signup_methods = django.dispatch.Signal()


def all_signup_methods():
    for _, methods in register_signup_methods.send(None):
        yield from methods


def signup_method_from_slug(slug, shift=None):
    for method in all_signup_methods():
        if method.slug == slug:
            return method(shift)
    raise ValueError(_("Signup Method '{slug}' was not found.").format(slug=slug))


@dataclass(frozen=True)
class AbstractParticipant:
    first_name: str
    last_name: str
    qualifications: QuerySet = field(hash=False)
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

    @functools.lru_cache(maxsize=1)
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


@dataclass(frozen=True)
class LocalUserParticipant(AbstractParticipant):
    user: get_user_model()

    def new_participation(self, shift):
        return LocalParticipation(shift=shift, user=self.user)

    def participation_for(self, shift):
        try:
            return LocalParticipation.objects.get(shift=shift, user=self.user)
        except LocalParticipation.DoesNotExist:
            return None


class ParticipationError(ValidationError):
    pass


class BaseSignupView(View):
    shift: Shift = ...
    method: "BaseSignupMethod" = ...

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
                self.method.perform_signup(self.request.user.as_participant(), **signup_kwargs)
                messages.success(
                    self.request,
                    self.method.signup_success_message.format(shift=self.shift),
                )
        except ParticipationError as errors:
            for error in errors:
                messages.error(self.request, self.method.signup_error_message.format(error=error))
        return redirect(self.shift.event.get_absolute_url())

    def decline_pressed(self, **decline_kwargs):
        try:
            with transaction.atomic():
                self.method.perform_decline(self.request.user.as_participant(), **decline_kwargs)
                messages.info(
                    self.request, self.method.decline_success_message.format(shift=self.shift)
                )
        except ParticipationError as errors:
            for error in errors:
                messages.error(self.request, self.method.decline_error_message.format(error=error))
        return redirect(self.shift.event.get_absolute_url())


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


class BaseSignupMethod:
    @property
    def slug(self):
        raise NotImplementedError()

    @property
    def verbose_name(self):
        raise NotImplementedError()

    description = """"""
    signup_view_class = BaseSignupView
    configuration_form_class = forms.Form

    # use _ == gettext_lazy!
    registration_button_text = _("Sign up")
    signup_success_message = _("You have successfully signed up for {shift}.")
    signup_error_message = _("Signing up failed: {error}")
    decline_success_message = _("You have successfully declined {shift}.")
    decline_error_message = _("Declining failed: {error}")

    """
    This form will be used for participations in disposition.
    Set to None if you don't want to support the default disposition.
    """
    disposition_participation_form_class = BaseDispositionParticipationForm
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
    def signup_checkers(self):
        return [
            check_event_is_active,
            check_participation_state_for_signup,
            check_inside_signup_timeframe,
            check_participant_age,
        ]

    @property
    def decline_checkers(self):
        return [
            check_event_is_active,
            check_participation_state_for_decline,
            check_inside_signup_timeframe,
        ]

    @functools.lru_cache()
    def get_signup_errors(self, participant) -> List[ParticipationError]:
        return [
            error
            for checker in self.signup_checkers
            if (error := checker(self, participant)) is not None
        ]

    @functools.lru_cache()
    def get_decline_errors(self, participant):
        return [
            error
            for checker in self.decline_checkers
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
        Configure a participation object for the given participant according to the method's configuration.
        `kwargs` may contain further instructions from e.g. a form.
        """
        if errors := self.get_signup_errors(participant):
            raise ParticipationError(errors)
        return self.get_participation_for(participant)

    def perform_decline(self, participant, **kwargs):
        """Create and configure a declining participation object for the given participant. `kwargs` may contain further instructions from a e.g. a form."""
        if errors := self.get_decline_errors(participant):
            raise ParticipationError(errors)
        participation = self.get_participation_for(participant)
        participation.state = AbstractParticipation.States.USER_DECLINED
        participation.save()
        return participation

    def get_configuration_fields(self):
        return {
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
                "format": functools.partial(formats.date_format, format="SHORT_DATETIME_FORMAT"),
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

    def get_signup_info(self):
        """
        Return key/value pairs about the configuration to show in the shift info box.
        """
        fields = self.get_configuration_fields()
        return {
            label: field.get("format", str)(value)
            for key, field in fields.items()
            if (label := field.get("publish_with_label", False))
            and (value := getattr(self.configuration, key))
        }

    def render_shift_state(self, request):
        """
        Render html that will be shown in the shift info box.
        Use it to inform about the current state of the shift and participations.
        """
        return ""

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
            template_string="{% load bootstrap4 %}{% bootstrap_form form %}"
        ).render(Context({"form": form}))
        return template
