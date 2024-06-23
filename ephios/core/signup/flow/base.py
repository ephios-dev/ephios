import functools
import logging
from argparse import Namespace
from collections import OrderedDict

from django import forms
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.services.notifications.types import (
    ResponsibleConfirmedParticipationDeclinedNotification,
    ResponsibleParticipationStateChangeNotification,
)
from ephios.core.signup.flow.abstract import AbstractSignupFlow
from ephios.core.signup.flow.participant_validation import BaseSignupActionValidator
from ephios.core.signup.forms import SignupConfigurationForm
from ephios.core.signup.participants import AbstractParticipant
from ephios.extra.utils import format_anything
from ephios.extra.widgets import CustomSplitDateTimeWidget

logger = logging.getLogger(__name__)


class BasicSignupFlowConfigurationForm(SignupConfigurationForm):
    """
    Configuration form with basic fields relevant for most signup flows.
    """

    signup_until = forms.SplitDateTimeField(
        required=False,
        widget=CustomSplitDateTimeWidget,
        initial=None,
        label=_("Signup until"),
    )
    user_can_decline_confirmed = forms.BooleanField(
        label=_("Confirmed users can decline by themselves"),
        required=False,
        help_text=_("only if the signup timeframe has not ended"),
    )
    user_can_customize_signup_times = forms.BooleanField(
        label=_("Users can provide individual start and end times"),
        required=False,
        initial=True,
    )


class BaseSignupFlow(AbstractSignupFlow):
    """
    Signup flow with some base implementations for common methods.
    """

    @property
    def configuration_form_class(self):
        return BasicSignupFlowConfigurationForm

    @property
    def signup_action_validator_class(self):
        return BaseSignupActionValidator

    @functools.lru_cache(1)
    def get_validator(self, participant):
        return self.signup_action_validator_class(self.shift, participant)

    def perform_signup(
        self, participant: AbstractParticipant, participation=None, acting_user=None, **kwargs
    ) -> AbstractParticipation:
        """
        Creates and/or configures a participation object for a given participant and sends out notifications.
        Passes the participation and kwargs to configure_participation to do configuration specific to the signup flow.
        """
        from ephios.core.services.notifications.types import (
            ResponsibleParticipationAwaitsDispositionNotification,
        )

        participation = participation or self.get_or_create_participation_for(participant)
        participation = self._configure_participation(participation, **kwargs)
        participation.save()
        if participation.state == AbstractParticipation.States.REQUESTED:
            ResponsibleParticipationAwaitsDispositionNotification.send(
                participation, acting_user=acting_user
            )
        else:
            ResponsibleParticipationStateChangeNotification.send(
                participation, acting_user=acting_user
            )
        return participation

    def perform_decline(self, participant, participation=None, **kwargs):
        """Create and configure a declining participation object for the given participant. `kwargs` may contain further instructions from a e.g. a form."""
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
        `kwargs` contains the signup form's cleaned_data. The participation object will be saved after this method.
        Return the participation.
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

    def get_configuration_form(self, *args, **kwargs):
        if self.shift is not None:
            kwargs.setdefault("initial", self.configuration.__dict__)
        kwargs.setdefault("event", self.event)
        kwargs.setdefault("shift", self.shift)
        kwargs.setdefault("description", self.description)
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
            for key, value in shift.signup_flow_configuration.items():
                setattr(self.configuration, key, value)
