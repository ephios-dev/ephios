import functools
import logging
from abc import ABC
from argparse import Namespace
from collections import OrderedDict

from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.services.notifications.types import (
    ResponsibleConfirmedParticipationDeclinedNotification,
)
from ephios.core.signals import register_signup_methods
from ephios.core.signup.participants import AbstractParticipant
from ephios.core.signup.stats import SignupStats
from ephios.extra.utils import format_anything

logger = logging.getLogger(__name__)


def installed_signup_methods():
    for _, methods in register_signup_methods.send_to_all_plugins(None):
        yield from methods


def enabled_signup_methods():
    for _, methods in register_signup_methods.send(None):
        yield from methods


def signup_method_from_slug(slug, shift=None, event=None):
    for method in installed_signup_methods():
        if method.slug == slug:
            return method(shift, event=event)
    raise ValueError(_("Signup Method '{slug}' was not found.").format(slug=slug))


class AbstractSignupMethod(ABC):
    """
    Abstract base class for signup methods.

    A signup method is a way to sign up for a shift.
    It combines logic for checking whether a participant can sign up for a shift,
    and creating participations.

    It also provides views for signing up using the web interface and forms for
    disposition and configuration.
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

    def get_validator(self, participant):
        """
        Return a SignupActionValidator for this signup method.
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
    def signup_view(self):
        """
        This view will be used to sign up for shifts.
        """
        raise NotImplementedError()

    def get_configuration_form(self):
        """
        This form will be used to configure this signup method.
        The cleaned data will be saved to shift.signup_configuration
        """
        raise NotImplementedError()

    def render(self, context):
        """
        Render the state/participations of the shift.
        Match the signature of template.render for use with the include template tag:
        {% include shift.signup_method %}
        By default, this loads `shift_state_template_name` and renders it using context from `get_shift_state_context_data`.
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

    def has_customized_signup(self, participation):
        """
        Return whether the participation was customized in a way specific to this signup method.
        """
        # This method should most likely check the participation's data attribute for modifications it has done.
        # 'customized' in this context means that the dispositioning person should give special attention to this participation.
        return False

    def get_or_create_participation_for(self, participant) -> AbstractParticipation:
        return participant.participation_for(self.shift) or participant.new_participation(
            self.shift
        )

    def perform_signup(
        self, participant: AbstractParticipant, participation=None, **kwargs
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


class BaseSignupMethod(AbstractSignupMethod):
    # pylint: disable=too-many-public-methods

    @property
    def disposition_participation_form_class(self):
        from .disposition import BaseDispositionParticipationForm

        return BaseDispositionParticipationForm

    @property
    def configuration_form_class(self):
        from ephios.core.signup.forms import BaseSignupMethodConfigurationForm

        return BaseSignupMethodConfigurationForm

    @property
    def signup_view_class(self):
        from ephios.core.signup.views import BaseSignupView

        return BaseSignupView

    @property
    def shift_state_template_name(self):
        raise NotImplementedError

    @property
    def signup_view(self):
        return self.signup_view_class.as_view(method=self, shift=self.shift)

    @property
    def signup_action_validator_class(self):
        from ephios.core.signup.checker import BaseSignupActionValidator

        return BaseSignupActionValidator

    @functools.lru_cache(1)
    def get_validator(self, participant):
        return self.signup_action_validator_class(self, participant)

    def perform_signup(
        self, participant: AbstractParticipant, participation=None, **kwargs
    ) -> AbstractParticipation:
        """
        Creates and/or configures a participation object for a given participant and sends out notifications.
        Passes the participation and kwargs to configure_participation to do configuration specific to the signup method.
        """
        from ephios.core.services.notifications.types import (
            ResponsibleParticipationRequestedNotification,
        )

        participation = participation or self.get_or_create_participation_for(participant)
        participation = self._configure_participation(participation, **kwargs)
        participation.save()
        ResponsibleParticipationRequestedNotification.send(participation)
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
        `kwargs` contains the signup form's cleaned_data.
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

    def get_participant_count_bounds(self):
        return None, None

    def get_signup_stats(self) -> "SignupStats":
        min_count, max_count = self.get_participant_count_bounds()
        participations = list(self.shift.participations.all())
        confirmed_count = sum(
            p.state == AbstractParticipation.States.CONFIRMED for p in participations
        )
        return SignupStats(
            requested_count=sum(
                p.state == AbstractParticipation.States.REQUESTED for p in participations
            ),
            confirmed_count=confirmed_count,
            missing=max(min_count - confirmed_count, 0) if min_count else 0,
            free=max(max_count - confirmed_count, 0) if max_count else None,
            min_count=min_count,
            max_count=max_count,
        )

    def render(self, context):
        try:
            with context.update(self.get_shift_state_context_data(context.request)):
                return get_template(self.shift_state_template_name).template.render(context)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Shift #{self.shift.pk} state render failed")
            with context.update({"exception_message": getattr(e, "message", None)}):
                return get_template("core/fragments/signup_method_missing.html").template.render(
                    context
                )

    def get_shift_state_context_data(self, request, **kwargs):
        """
        Additionally to the context of the event detail view, provide context for rendering `shift_state_template_name`.
        """
        kwargs["shift"] = self.shift
        kwargs["participations"] = self.shift.participations.filter(
            state__in={
                AbstractParticipation.States.REQUESTED,
                AbstractParticipation.States.CONFIRMED,
            }
        ).order_by("-state")
        if self.disposition_participation_form_class is not None:
            kwargs["disposition_url"] = (
                reverse("core:shift_disposition", kwargs={"pk": self.shift.pk})
                if request.user.has_perm("core.change_event", obj=self.shift.event)
                else None
            )
        return kwargs

    def get_participation_display(self):
        """
        Returns a displayable representation of participation that can be rendered into a table (e.g. for pdf export).
        Must return a list of participations or empty slots. Each element of the list has to be a list of a fixed
        size where each entry is rendered to a separate column.
        Ex.: [["participant1_name", "participant1_qualification"], ["participant2_name", "participant2_qualification"]]
        """
        return [[participant.display_name] for participant in self.shift.get_participants()]

    def get_configuration_form(self, *args, **kwargs):
        if self.shift is not None:
            kwargs.setdefault("initial", self.configuration.__dict__)
        if self.event is not None:
            kwargs.setdefault("event", self.event)
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
            for key, value in shift.signup_configuration.items():
                setattr(self.configuration, key, value)
