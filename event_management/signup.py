import functools
import json
from argparse import Namespace
from dataclasses import dataclass
from datetime import date
from typing import List

import django.dispatch
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.dispatch import receiver
from django import forms
from django.template import Template, Context
from django.utils import timezone, dateparse, formats
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect

from django.db.models import QuerySet
from django.views import View

from contrib.json import CustomJSONDecoder, CustomJSONEncoder
from event_management.models import LocalParticipation, AbstractParticipation, Shift
from user_management.models import Qualification

register_signup_methods = django.dispatch.Signal(providing_args=[])


def all_signup_methods():
    for _, methods in register_signup_methods.send(None):
        yield from methods


def signup_method_from_slug(slug, shift=None):
    for method in all_signup_methods():
        if method.slug == slug:
            return method(shift)
    raise ValueError(_("Signup Method '{slug}' was not found.").format(slug=slug))


@dataclass
class AbstractParticipator:
    first_name: str
    last_name: str
    qualifications: QuerySet
    date_of_birth: date

    @property
    def age(self):
        today, born = date.today(), self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def create_participation(self, shift):
        raise NotImplementedError

    def participation_for(self, shift):
        """Return the participation object for a shift. Return None if it does not exist."""
        raise NotImplementedError

    def collect_all_qualifications(self):
        """We collect using breath first search with one query for every layer of inclusion."""
        all_qualifications = set(self.qualifications)
        current = self.qualifications
        while current:
            next = (
                Qualification.objects.filter(included_by__in=current)
                .exclude(id__in=(q.id for q in all_qualifications))
                .distinct()
            )
            all_qualifications |= set(next)
            current = next
        return all_qualifications

    def has_qualifications(self, qualifications):
        return set(qualifications) <= self.collect_all_qualifications()


@dataclass
class LocalUserParticipator(AbstractParticipator):
    user: get_user_model()

    def create_participation(self, shift):
        return LocalParticipation.objects.create(shift=shift, user=self.user)

    def participation_for(self, shift):
        try:
            return LocalParticipation.objects.get(shift=shift, user=self.user)
        except LocalParticipation.DoesNotExist:
            return None


class ParticipationError(ValidationError):
    pass


class ConfigurationForm(forms.Form):
    def get_configuration(self):
        return json.dumps(self.cleaned_data, cls=CustomJSONEncoder)


def check_event_is_active(method, participator):
    if not method.shift.event.active:
        return ParticipationError(_("The event is not active."))


def check_participation_state_for_signup(method, participator):
    participation = participator.participation_for(method.shift)
    if participation is not None:
        if participation.state == AbstractParticipation.REQUESTED:
            return ParticipationError(
                _("You have already requested your participation for {shift}").format(
                    shift=method.shift
                )
            )
        elif participation.state == AbstractParticipation.CONFIRMED:
            return ParticipationError(
                _("You are bindingly signed up for {shift}.").format(shift=method.shift)
            )
        elif participation.state == AbstractParticipation.RESPONSIBLE_REJECTED:
            return ParticipationError(
                _("You are rejected from {shift}.").format(shift=method.shift)
            )


def check_participation_state_for_decline(method, participator):
    participation = participator.participation_for(method.shift)
    if participation is not None:
        if participation.state == AbstractParticipation.CONFIRMED:
            return ParticipationError(
                _("You are bindingly signed up for {shift}.").format(shift=method.shift)
            )
        elif participation.state == AbstractParticipation.RESPONSIBLE_REJECTED:
            return ParticipationError(
                _("You are rejected from {shift}.").format(shift=method.shift)
            )
        elif participation.state == AbstractParticipation.USER_DECLINED:
            return ParticipationError(
                _("You have already declined participating in {shift}.").format(shift=method.shift)
            )


def check_inside_signup_timeframe(method, participator):
    last_time = method.shift.end_time
    if method.configuration.signup_until is not None:
        last_time = min(last_time, method.configuration.signup_until)
    if timezone.now() > last_time:
        return ParticipationError(_("The signup period is over."))


def check_participator_age(method, participator):
    minimum_age = method.configuration.minimum_age
    if minimum_age is not None and participator.age < minimum_age:
        return ParticipationError(
            _("You are too young. The minimum age is {age}.").format(age=minimum_age)
        )


class BaseSignupMethod:
    slug = "abstract"
    verbose_name = "abstract"
    description = """"""
    registration_button_text = _("Sign up")

    def __init__(self, shift):
        self.shift = shift
        self.configuration = Namespace(
            **{name: config["default"] for name, config in self.get_configuration_fields().items()}
        )
        if shift is not None:
            for key, value in json.loads(
                shift.signup_configuration if shift is not None else "{}", cls=CustomJSONDecoder
            ).items():
                setattr(self.configuration, key, value)

    @property
    def signup_view_class(self):
        return BaseSignupView

    @cached_property
    def signup_view(self):
        return self.signup_view_class.as_view(method=self, shift=self.shift)

    @property
    def signup_checkers(self):
        return [
            check_event_is_active,
            check_participation_state_for_signup,
            check_inside_signup_timeframe,
            check_participator_age,
        ]

    @property
    def decline_checkers(self):
        return [
            check_event_is_active,
            check_participation_state_for_decline,
            check_inside_signup_timeframe,
            check_participator_age,
        ]

    def get_signup_errors(self, participator) -> List[ParticipationError]:
        return [
            error
            for checker in self.signup_checkers
            if (error := checker(self, participator)) is not None
        ]

    def get_decline_errors(self, participator):
        return [
            error
            for checker in self.decline_checkers
            if (error := checker(self, participator)) is not None
        ]

    def can_decline(self, participator):
        return not self.get_decline_errors(participator)

    def can_sign_up(self, participator):
        return not self.get_signup_errors(participator)

    def get_participation_for(self, participator):
        return participator.participation_for(self.shift) or participator.create_participation(
            self.shift
        )

    def perform_signup(self, participator: AbstractParticipator, **kwargs):
        """Create and configure a participation object for the given participator. `kwargs` may contain further instructions from a e.g. a form."""
        if errors := self.get_signup_errors(participator):
            raise ParticipationError(errors)
        return self.get_participation_for(participator)

    def perform_decline(self, participator, **kwargs):
        """Create and configure a declining participation object for the given participator. `kwargs` may contain further instructions from a e.g. a form."""
        if errors := self.get_decline_errors(participator):
            raise ParticipationError(errors)
        participation = self.get_participation_for(participator)
        participation.state = AbstractParticipation.USER_DECLINED
        participation.save()
        return participation

    def get_configuration_fields(self):
        return {
            "minimum_age": {
                "formfield": forms.IntegerField(required=False),
                "default": 16,
                "publish_with_label": _("Minimum age"),
            },
            "signup_until": {
                "formfield": forms.SplitDateTimeField(required=False),
                "default": None,
                "publish_with_label": _("Signup until"),
                "format": functools.partial(formats.date_format, format="SHORT_DATETIME_FORMAT"),
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

    def render_shift_state(self):
        """
        Render html that will be shown in the shift info box.
        Use it to inform about the current state of the shift and participations.
        """
        return ""

    def get_configuration_form(self, *args, **kwargs):
        if self.shift is not None:
            kwargs.setdefault("initial", self.configuration.__dict__)
        form = ConfigurationForm(*args, **kwargs)
        for name, config in self.get_configuration_fields().items():
            form.fields[name] = config["formfield"]
        return form

    def render_configuration_form(self, form=None, *args, **kwargs):
        form = form or self.get_configuration_form(*args, **kwargs)
        template = Template(
            template_string="{% load bootstrap4 %}{% bootstrap_form form %}"
        ).render(Context({"form": form}))
        return template

    # menschenlesbare Füllstandsangabe (z.B. 3/8, 3/, 0/8 (4 interessiert)) vlt irgendwie mit weiteren color-coded Status wie [“Egal”, Helfers needed", “genug Interesse”, “voll besetzt”]

    # HTML-Darstellung der Helfer (defaults to an unorderd list of Helfers)
    # Helferlisten-PDF-content (defautls to an unorderd list of Helfers)


class BaseSignupView(View):
    shift: Shift = ...
    method: BaseSignupMethod = ...

    def dispatch(self, request, *args, **kwargs):
        if (choice := request.POST.get("signup_choice")) is not None:
            if choice == "sign_up":
                return self.signup_pressed(request, *args, **kwargs)
            elif choice == "decline":
                return self.decline_pressed(request, *args, **kwargs)
            else:
                raise ValueError(
                    _("'{choice}' is not a valid signup action.").format(choice=choice)
                )
        return super().dispatch(request, *args, **kwargs)

    def signup_pressed(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                self.method.perform_signup(request.user.as_participator())
                messages.success(
                    request,
                    _("You have successfully signed up for shift {shift}.").format(
                        shift=self.shift
                    ),
                )
        except ParticipationError as errors:
            for error in errors:
                messages.error(request, _("Signing up failed: ") + str(error))
        finally:
            return redirect(self.shift.event.get_absolute_url())

    def decline_pressed(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                self.method.perform_decline(request.user.as_participator())
                messages.info(
                    request, _("You have successfully declined {shift}.").format(shift=self.shift)
                )
        except ParticipationError as errors:
            for error in errors:
                messages.error(request, _("Declining failed: ") + str(error))
        finally:
            return redirect(self.shift.event.get_absolute_url())
