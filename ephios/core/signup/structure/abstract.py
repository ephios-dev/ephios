import logging
from abc import ABC

from ephios.core.signup.stats import SignupStats

logger = logging.getLogger(__name__)


class AbstractShiftStructure(ABC):
    """
    Abstract base class for shift structure.

    A shift structure defines what a participant does inside the shift.
    There may be no structure at all or some elaborate staff hierarchy.

    The structure is responsible for rendering the participations of the shift.
    """

    def __init__(self, shift, event=None):
        self.shift = shift
        self.event = getattr(shift, "event", event)

    @property
    def slug(self):
        """
        A unique identifier for this structure.
        """
        raise NotImplementedError()

    @property
    def verbose_name(self):
        """
        The human-readable name of this structure.
        """
        raise NotImplementedError()

    @property
    def description(self):
        """
        A human-readable description of this structure.
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
    def signup_form_class(self):
        """
        This form will be used for participations in signup.
        """
        raise NotImplementedError()

    def get_configuration_form(self):
        """
        This form will be used to configure this structure.
        The cleaned data will be saved to shift.structure_configuration
        """
        raise NotImplementedError()

    def get_checkers(self):
        """
        Return a list of checkers that should be run when validating signup actions.
        """
        raise NotImplementedError()

    def render(self, context):
        """
        Render the state/participations of the shift.
        Match the signature of template.render for use with the include template tag:
        {% include shift.structure %}
        By default, this loads `shift_state_template_name` and renders it using context from `get_shift_state_context_data`.
        """
        raise NotImplementedError()

    def get_signup_info(self):
        """Return key/value pairs about the configuration to show in exports etc."""
        raise NotImplementedError()

    def get_participation_display(self):
        raise NotImplementedError()

    def get_participant_count_bounds(self):
        """
        Return a tuple of min, max for how many participants are allowed for the shift.
        Use None for any value if it is not specifiable."""
        raise NotImplementedError()

    def get_signup_stats(self) -> "SignupStats":
        """
        Return an instance of SignupStats for the shift.
        """
        raise NotImplementedError()

    def has_customized_signup(self, participation):
        """
        Return whether the participation was customized in a way specific to this shift structure.
        """
        # This method should most likely check the participation's data attribute for modifications it has done.
        # 'customized' in this context means that the dispositioning person should give special attention to this participation.
        return False
