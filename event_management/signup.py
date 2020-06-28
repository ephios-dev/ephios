from dataclasses import dataclass
from datetime import date

import django.dispatch
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.shortcuts import redirect

from event_management.models import LocalParticipation, AbstractParticipation

register_signup_method = django.dispatch.Signal(providing_args=[])


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


class LocalUserParticipator(AbstractParticipator):
    user: get_user_model()

    def create_participation(self, shift):
        return LocalParticipation.objects.create(shift=shift, user=self.user)

    def participation_for(self, shift):
        try:
            return LocalParticipation.objects.get(shift=shift, user=self.user)
        except LocalParticipation.DoesNotExist:
            return None


class SignupError(Excpetion):
    pass


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

    def check_signup(participator):
        self.check_no_existing_participation(participator)
        self.check_inside_signup_timeframe()
        self.check_participator_age(participator)

    def check_no_existing_participation(self, participator):
        if participator.participation_for(self.shift):
            raise SignupError(_("You are already signed up for this shift."))

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
        self.create_participation(request.user.as_participator())
        return redirect("event_management:event_detail", pk=self.shift.event.pk)

    # Konfigurationsformular für den Verwalter
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
        participation = super().create_participation(participator)
        participation.state = AbstractParticipation.CONFIRMED
        participation.save()
        return participation







