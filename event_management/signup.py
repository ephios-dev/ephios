from dataclasses import dataclass
from datetime import date

import django.dispatch
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.shortcuts import redirect

from event_management.models import LocalParticipation

register_signup_method = django.dispatch.Signal(providing_args=[])


@dataclass
class AbstractParticipator:
    first_name: str
    last_name: str
    qualifications: list
    date_of_birth: date

    def create_participation(self, shift)rg:
        raise NotImplementedError


class LocalUserParticipator(AbstractParticipator):
    user: get_user_model()

    def create_participation(self, shift):
        return LocalParticipation.objects.create(shift=shift, user=self.user)


class AbstractSignupMethod:
    slug = "abstract"
    verbose_name = "abstract"
    description = """"""
    registration_button_text = _("Sign up")

    def __init__(self, shift):
        self.shift = shift

    def can_sign_up(self, participator, shift):
        return all(
            self.check_participator_age(participator, shift),
            self.check_meldezeitraum(shift),
        )

    def create_participation(self, participator):
        """Create and configure a participation object for the given participator."""
        # TODO check if its ok to create a participation and that there isn't one already. Throw a custom Errors.
        participator.create_participation(self.shift)

    def signup_view(self, request, *args, **kwargs):
        self.create_participation(request.user.as_participator())
        return redirect("event_management:event_detail", pk=self.shift.event.pk)

    # Konfigurationsformular für den Verwalter
    # menschenlesbare Füllstandsangabe (z.B. 3/8, 3/, 0/8 (4 interessiert)) vlt irgendwie mit weiteren color-coded Status wie [“Egal”, Helfers needed", “genug Interesse”, “voll besetzt”]

    # HTML-Darstellung der Helfer (defaults to an unorderd list of Helfers)
    # Helferlisten-PDF-content (defautls to an unorderd list of Helfers)
    # Helfer kann sich überhaupt auf diese Schicht anmelden (defaults apply)
