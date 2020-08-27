import json
from dataclasses import dataclass
from datetime import date

import django.dispatch
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.dispatch import receiver
from django.forms import Form, IntegerField, DateField
from django.template import Template, Context
from django.utils.translation import gettext as _
from django.shortcuts import redirect

from event_management.models import LocalParticipation, AbstractParticipation
from jep.widgets import CustomDateInput

register_signup_methods = django.dispatch.Signal(providing_args=[])


def signup_method_from_slug(slug, shift=None):
    for receiver, method in register_signup_methods.send(None):
        if method.slug == slug:
            return method(shift)
    raise ValueError(f"Signup Method '{slug}' was not found.")


@dataclass
class AbstractParticipator:
    first_name: str
    last_name: str
    qualifications: list
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


class AbstractSignupConfigurationForm(Form):
    minimum_age = IntegerField(initial=16)
    signup_until = DateField(required=False, widget=CustomDateInput())

    def get_configuration(self):
        return json.dumps(self.cleaned_data, cls=DjangoJSONEncoder)


class AbstractSignupMethod:
    slug = "abstract"
    verbose_name = "abstract"
    description = """"""
    registration_button_text = _("Sign up")

    def __init__(self, shift):
        self.shift = shift

    def can_sign_up(self, participator):
        try:
            self.check_signup(participator)
        except SignupError:
            return False
        return True

    def check_signup(self, participator):
        self.check_event_is_active()
        self.check_participation_state(participator)
        self.check_inside_signup_timeframe()
        self.check_participator_age(participator)

    def check_event_is_active(self):
        if not self.shift.event.active:
            raise SignupError(_("The event is not active, you cannot sign up for it."))

    def check_participation_state(self, participator):
        participation = participator.participation_for(self.shift)
        if participation is not None:
            if participation.state == AbstractParticipation.REQUESTED:
                raise SignupError(
                    _(f"You have already requested your participation for shift {self.shift}.")
                )
            elif participation.state == AbstractParticipation.CONFIRMED:
                raise SignupError(_(f"You are already signed up for shift {self.shift}."))
            elif participation.state == AbstractParticipation.RESPONSIBLE_REJECTED:
                raise SignupError(_(f"You are rejected from shift {self.shift}."))
            elif participation.state == AbstractParticipation.USER_DECLINED:
                participation.state = AbstractParticipation.REQUESTED

    def check_inside_signup_timeframe(self):
        ...  # TODO
        if False:
            raise SignupError(_("The signup period is over."))

    def check_participator_age(self, participator):
        # TODO get minimum age from self.shift.configuration
        ...
        minimum_age = 16
        if participator.age < minimum_age:
            raise SignupError(_(f"Too young. The minimum age is {minimum_age}."))

    def create_participation(self, participator):
        """Create and configure a participation object for the given participator."""
        self.check_signup(participator)
        return participator.create_participation(self.shift)

    def signup_view(self, request, *args, **kwargs):
        try:
            participation = self.create_participation(request.user.as_participator())
            messages.success(
                request, _(f"You have successfully signed up for shift {participation.shift}."),
            )
        except SignupError as e:
            messages.error(request, e)
        return redirect("event_management:event_detail", pk=self.shift.event.pk)

    def get_configuration_form(self, *args, **kwargs):
        return AbstractSignupConfigurationForm(*args, **kwargs)

    def render_configuration_form(self, form=None, *args, **kwargs):
        form = form or self.get_configuration_form(*args, **kwargs)
        template = Template(
            template_string="{% load bootstrap4 %}{% bootstrap_form form %}"
        ).render(Context({"form": form}))
        return template

    # menschenlesbare Füllstandsangabe (z.B. 3/8, 3/, 0/8 (4 interessiert)) vlt irgendwie mit weiteren color-coded Status wie [“Egal”, Helfers needed", “genug Interesse”, “voll besetzt”]

    # HTML-Darstellung der Helfer (defaults to an unorderd list of Helfers)
    # Helferlisten-PDF-content (defautls to an unorderd list of Helfers)


####################
# BUILT IN METHODS #
####################

# these could be moved to a contrib module somewhere else


class InstantConfirmationSignupMethod(AbstractSignupMethod):
    slug = "instant_confirmation"
    verbose_name = _("Instant Confirmation")
    description = _("""This method instantly confirms a signup.""")

    def create_participation(self, participator):
        if (participation := participator.participation_for(self.shift)) is None:
            participation = super().create_participation(participator)
        participation.state = AbstractParticipation.CONFIRMED
        participation.save()
        return participation


@receiver(register_signup_methods)
def register_signup_method(sender, **kwargs):
    return InstantConfirmationSignupMethod
