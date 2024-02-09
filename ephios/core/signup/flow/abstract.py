import logging
from abc import ABC

from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup.participants import AbstractParticipant

logger = logging.getLogger(__name__)


class AbstractSignupFlow(ABC):
    """
    Abstract base class for signup flow.

    A signup flow defines the logic for how a participant signs up for a shift.
    It checks if the participant is eligible to sign up, and if so, creates a participation object.
    It is not responsible for what the participant does inside the shift, only for the process of signing up.
    It provides forms for disposition and configuration.
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

    def get_or_create_participation_for(self, participant) -> AbstractParticipation:
        return participant.participation_for(self.shift) or participant.new_participation(
            self.shift
        )

    def perform_signup(
        self, participant: AbstractParticipant, participation=None, acting_user=None, **kwargs
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
        raise NotImplementedError()
