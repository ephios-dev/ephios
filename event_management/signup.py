import json
from argparse import Namespace
from dataclasses import dataclass
from datetime import date
from typing import List

import django.dispatch
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django import forms
from django.template import Template, Context
from django.utils import timezone, dateparse
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect

from django.db.models import QuerySet

from contrib.json import CustomJSONDecoder, CustomJSONEncoder
from event_management.models import LocalParticipation, AbstractParticipation
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
            next = Qualification.objects.filter(included_by__in=current).distinct()
            current = next - all_qualifications
            all_qualifications |= set(next)
        return all_qualifications

    def has_qualifications(self, qualifications):
        return not bool(set(qualifications).difference(self.collect_all_qualifications()))


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


class SignupError(Exception):
    pass


class DeclineError(Exception):
    pass


class ConfigurationForm(forms.Form):
    def get_configuration(self):
        return json.dumps(self.cleaned_data, cls=CustomJSONEncoder)


class AbstractSignupMethod:
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

    def can_sign_up(self, participator):
        return not self.get_signup_errors(participator)

    def get_signup_errors(self, participator) -> List[SignupError]:
        return [
            error
            for error in (
                self.check_event_is_active(),
                self.check_participation_state_for_signup(participator),
                self.check_inside_signup_timeframe(),
                self.check_participator_age(participator),
            )
            if error is not None
        ]

    def check_event_is_active(self):
        if not self.shift.event.active:
            return SignupError(_("The event is not active."))

    def check_participation_state_for_signup(self, participator):
        participation = participator.participation_for(self.shift)
        if participation is not None:
            if participation.state == AbstractParticipation.REQUESTED:
                return SignupError(
                    _("You have already requested your participation for shift {shift}").format(
                        shift=self.shift
                    )
                )
            elif participation.state == AbstractParticipation.CONFIRMED:
                return SignupError(
                    _("You are already signed up for shift {shift}").format(shift=self.shift)
                )
            elif participation.state == AbstractParticipation.RESPONSIBLE_REJECTED:
                return SignupError(
                    _("You are rejected from shift {shift}.").format(shift=self.shift)
                )
            elif participation.state == AbstractParticipation.USER_DECLINED:
                participation.state = AbstractParticipation.REQUESTED

    def check_inside_signup_timeframe(self):
        if (
            self.configuration.signup_until is not None
            and timezone.now() > self.configuration.signup_until
        ):
            return SignupError(_("The signup period is over."))

    def check_participator_age(self, participator):
        minimum_age = self.configuration.minimum_age
        if minimum_age is not None and participator.age < minimum_age:
            return SignupError(
                _("You are too young. The minimum age is {age}.").format(age=minimum_age)
            )

    def can_user_decline(self, participator):
        if participation := participator.participation_for(self.shift):
            return participation.state == AbstractParticipation.REQUESTED
        else:
            return True

    def create_participation(self, participator):
        """Create and configure a participation object for the given participator."""
        if errors := self.get_signup_errors(participator):
            raise SignupError(errors)
        return participator.create_participation(self.shift)

    def signup_view(self, request, *args, **kwargs):
        try:
            participation = self.create_participation(request.user.as_participator())
            messages.success(
                request,
                _("You have successfully signed up for shift {shift}.").format(
                    shift=participation.shift
                ),
            )
        except SignupError as e:
            messages.error(request, e)
        return redirect("event_management:event_detail", pk=self.shift.event.pk)

    def validate_participation_state_for_decline(self, participator):
        participation = participator.participation_for(self.shift)
        if participation is not None:
            if participation.state == AbstractParticipation.CONFIRMED:
                return DeclineError(
                    _("You are bindingly signed up for shift {shift}.").format(shift=self.shift)
                )
            elif participation.state == AbstractParticipation.RESPONSIBLE_REJECTED:
                return DeclineError(
                    _("You are rejected from shift {shift}.").format(shift=self.shift)
                )
            elif participation.state == AbstractParticipation.USER_DECLINED:
                return DeclineError(
                    _("You have already declined participating in shift {shift}.").format(
                        shift=self.shift
                    )
                )

    def decline_view(self, request):
        participator = request.user.as_participator()
        try:
            self.validate_participation_state_for_decline(participator)
        except DeclineError as e:
            messages.error(request, e)
        else:
            participation = self.create_participation(participator)
            participation.state = AbstractParticipation.USER_DECLINED
            participation.save()
            messages.info(
                request,
                _("You have declined a participation for shift {shift}.").format(shift=self.shift),
            )
        return self.shift.event.get_absolute_url()

    def get_configuration_fields(self):
        return {
            "minimum_age": {"formfield": forms.IntegerField(required=False), "default": 16},
            "signup_until": {
                "formfield": forms.SplitDateTimeField(required=False),
                "default": None,
            },
        }

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
