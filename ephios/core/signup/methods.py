import dataclasses
import functools
import logging
from argparse import Namespace
from collections import OrderedDict
from typing import List, Optional

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Field, Layout
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.template import Context, Template
from django.utils import timezone
from django.utils.functional import SimpleLazyObject, cached_property, classproperty
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from ephios.core.models import AbstractParticipation, Shift
from ephios.extra.widgets import CustomSplitDateTimeWidget

from ...extra.utils import format_anything
from ..signals import participant_from_request, register_signup_methods
from .participants import AbstractParticipant

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


class ParticipationError(ValidationError):
    pass


def prevent_getting_participant_from_request_user(request):
    original_user = request.user

    class ProtectedUser(SimpleLazyObject):
        def as_participant(self):
            raise Exception("Access of request.user.as_participant in SignupViews is not allowed.")

    request.user = ProtectedUser(lambda: original_user)


def get_nonlocal_participant_from_request(request):
    for _, participant in participant_from_request.send(sender=None, request=request):
        if participant is not None:
            return participant
    raise PermissionDenied


class BaseParticipationForm(forms.ModelForm):
    individual_start_time = forms.SplitDateTimeField(
        label=_("Individual start time"), widget=CustomSplitDateTimeWidget, required=False
    )
    individual_end_time = forms.SplitDateTimeField(
        label=_("Individual end time"),
        widget=CustomSplitDateTimeWidget,
        required=False,
    )

    # TODO: any validation (time subset of shift time etc?!)
    def clean_individual_start_time(self):
        if self.cleaned_data["individual_start_time"] == self.shift.start_time:
            return None
        return self.cleaned_data["individual_start_time"]

    def clean_individual_end_time(self):
        if self.cleaned_data["individual_end_time"] == self.shift.end_time:
            return None
        return self.cleaned_data["individual_end_time"]

    class Meta:
        model = AbstractParticipation
        fields = ["individual_start_time", "individual_end_time", "comment"]

    def __init__(self, *args, **kwargs):
        instance = kwargs["instance"]
        shift = getattr(self, "shift", instance.shift)
        kwargs["initial"] = {
            **kwargs.get("initial", {}),
            "individual_start_time": instance.individual_start_time or shift.start_time,
            "individual_end_time": instance.individual_end_time or shift.end_time,
        }
        super().__init__(*args, **kwargs)


class BaseSignupForm(BaseParticipationForm):
    def get_field_layout(self):
        return Layout(*(Field(name) for name in self.fields))

    def _get_main_submit_label(self):
        if (p := self.participant.participation_for(self.method.shift)) is not None and p.state in (
            AbstractParticipation.States.REQUESTED,
            AbstractParticipation.States.CONFIRMED,
        ):
            return _("Save")
        return self.method.registration_button_text

    def _get_buttons(self):
        buttons = [
            HTML(
                f'<button class="btn btn-success mt-1 me-1" type="submit" name="signup_choice" value="sign_up">{self._get_main_submit_label()}</button>'
            ),
            HTML(
                f'<a class="btn btn-secondary mt-1 float-end" href="{self.participant.reverse_event_detail(self.method.shift.event)}">{_("Cancel")}</a>'
            ),
        ]
        if self.method.can_decline(self.participant):
            buttons.append(
                HTML(
                    f'<button class="btn btn-secondary mt-1 me-1 float-end" type="submit" name="signup_choice" value="decline">{_("Decline")}</button>'
                )
            )
        return buttons

    def __init__(self, *args, **kwargs):
        self.method = kwargs.pop("method")
        self.shift = self.method.shift
        self.participant: AbstractParticipant = kwargs.pop("participant")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            self.get_field_layout(),
            FormActions(*self._get_buttons()),
        )
        if not self.shift.signup_method.configuration.user_can_customize_signup_times:
            self.fields["individual_start_time"].disabled = True
            self.fields["individual_end_time"].disabled = True


class BaseSignupView(FormView):
    """
    This View reacts to the signup or decline buttons being pressed using a POST request.
    Beware that request.user might be anonymous. You should only act on participants acquired
    using `get_participant`.
    """

    shift: Shift = ...
    method: "BaseSignupMethod" = ...
    form_class = BaseSignupForm
    template_name = "core/signup.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "method": self.method,
                "participant": self.participant,
                "instance": self.method.get_participation_for(self.participant),
            }
        )
        return kwargs

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.participant: AbstractParticipant = kwargs["participant"]
        prevent_getting_participant_from_request_user(request)

    def form_valid(self, form):
        if (choice := self.request.POST.get("signup_choice")) is not None:
            if choice == "sign_up":
                return self.signup_pressed(form)
            if choice == "decline":
                return self.decline_pressed(form)
        return self.form_invalid(form)

    def signup_pressed(self, form):
        try:
            with transaction.atomic():
                participation = form.save()
                self.method.perform_signup(self.participant, participation, **form.cleaned_data)
                messages.success(
                    self.request,
                    self.method.signup_success_message.format(shift=self.shift),
                )
        except ParticipationError as errors:
            for error in errors:
                messages.error(self.request, self.method.signup_error_message.format(error=error))
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def decline_pressed(self, form):
        try:
            with transaction.atomic():
                participation = form.save()
                self.method.perform_decline(self.participant, participation, **form.cleaned_data)
                messages.info(
                    self.request, self.method.decline_success_message.format(shift=self.shift)
                )
        except ParticipationError as errors:
            for error in errors:
                messages.error(self.request, self.method.decline_error_message.format(error=error))
        return redirect(self.participant.reverse_event_detail(self.shift.event))


def check_event_is_active(method, participant):
    if not method.shift.event.active:
        return ParticipationError(_("The event is not active."))


def check_participation_state_for_signup(method, participant):
    participation = participant.participation_for(method.shift)
    if participation is not None:
        if participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
            return ParticipationError(_("You have been rejected."))


def check_participation_state_for_decline(method, participant):
    participation = participant.participation_for(method.shift)
    if participation is not None:
        if (
            participation.state == AbstractParticipation.States.CONFIRMED
            and not method.configuration.user_can_decline_confirmed
        ):
            return ParticipationError(_("You cannot decline by yourself."))
        if participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
            return ParticipationError(_("You have been rejected."))
        if participation.state == AbstractParticipation.States.USER_DECLINED:
            return ParticipationError(_("You have already declined participating."))


def check_inside_signup_timeframe(method, participant):
    last_time = method.shift.end_time
    if method.configuration.signup_until is not None:
        last_time = min(last_time, method.configuration.signup_until)
    if timezone.now() > last_time:
        return ParticipationError(_("The signup period is over."))


def check_participant_age(method, participant):
    minimum_age = method.configuration.minimum_age
    day = method.shift.start_time.date()
    age = participant.get_age(day)
    if minimum_age is not None and age is not None and age < minimum_age:
        return ParticipationError(
            _("You are too young. The minimum age is {age}.").format(age=minimum_age)
        )


def get_conflicting_participations(shift, participant: AbstractParticipant):
    self_start_time = shift.start_time
    self_end_time = shift.end_time
    if self_participation := participant.participation_for(shift):
        self_start_time = self_participation.start_time
        self_end_time = self_participation.end_time
    return participant.all_participations().filter(
        ~Q(shift=shift)
        & Q(state=AbstractParticipation.States.CONFIRMED)
        & Q(start_time__lt=self_end_time, end_time__gt=self_start_time)
    )


def check_conflicting_shifts(method, participant):
    if get_conflicting_participations(method.shift, participant).exists():
        return ParticipationError(_("You are already confirmed for another shift at this time."))


class BaseSignupMethodConfigurationForm(forms.Form):
    minimum_age = forms.IntegerField(
        required=False, min_value=1, max_value=999, initial=None, label=_("Minimum age")
    )
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


class BaseSignupMethod:
    # pylint: disable=too-many-public-methods

    @property
    def slug(self):
        raise NotImplementedError()

    @property
    def verbose_name(self):
        raise NotImplementedError()

    @property
    def disposition_participation_form_class(self):
        """
        This form will be used for participations in disposition.
        Set to None if you don't want to support the default disposition.
        """
        from .disposition import BaseDispositionParticipationForm

        return BaseDispositionParticipationForm

    configuration_form_class = BaseSignupMethodConfigurationForm

    @property
    def signup_view_class(self):
        return BaseSignupView

    description = """"""

    # use _ == gettext_lazy!
    registration_button_text = _("Sign up")
    signup_success_message = _("You have successfully signed up for {shift}.")
    signup_error_message = _("Signing up failed: {error}")
    decline_success_message = _("You have successfully declined {shift}.")
    decline_error_message = _("Declining failed: {error}")

    uses_requested_state = True

    def __init__(self, shift, event=None):
        self.shift = shift
        self.event = getattr(shift, "event", event)

        self.configuration = Namespace(
            **{
                name: field.initial
                for name, field in self.configuration_form_class.base_fields.items()
            }
        )
        if shift is not None:
            for key, value in shift.signup_configuration.items():
                setattr(self.configuration, key, value)

    @cached_property
    def signup_view(self):
        return self.signup_view_class.as_view(method=self, shift=self.shift)

    @property
    def _signup_checkers(self):
        return [
            check_event_is_active,
            check_participation_state_for_signup,
            check_inside_signup_timeframe,
            check_participant_age,
            check_conflicting_shifts,
        ]

    @property
    def _decline_checkers(self):
        return [
            check_event_is_active,
            check_participation_state_for_decline,
            check_inside_signup_timeframe,
        ]

    @functools.lru_cache()
    def get_signup_errors(self, participant) -> List[ParticipationError]:
        return [
            error
            for checker in self._signup_checkers
            if (error := checker(self, participant)) is not None
        ]

    @functools.lru_cache()
    def get_decline_errors(self, participant):
        return [
            error
            for checker in self._decline_checkers
            if (error := checker(self, participant)) is not None
        ]

    def can_decline(self, participant):
        """
        Return whether the participant is allowed to decline.
        """
        return not self.get_decline_errors(participant)

    def can_sign_up(self, participant):
        """
        Return whether the participant is allowed to perform signup.
        Note that this should also return True for participants allowed to customize their participation.
        """
        valid_state = (p := participant.participation_for(self.shift)) is None or p.state not in (
            AbstractParticipation.States.CONFIRMED,
            AbstractParticipation.States.REQUESTED,
        )
        return valid_state and not self.get_signup_errors(participant)

    def can_customize_signup(self, participant):
        """
        Return whether the participant gets shown the option to customize their participation.
        """
        # We check for decline as well in case the participation is already requested/confirmed.
        declineable_state = (
            p := participant.participation_for(self.shift)
        ) is not None and p.state in (
            AbstractParticipation.States.CONFIRMED,
            AbstractParticipation.States.REQUESTED,
        )
        return not self.get_signup_errors(participant) and (
            not declineable_state or self.can_decline(participant)
        )

    def get_participation_for(self, participant) -> AbstractParticipation:
        return participant.participation_for(self.shift) or participant.new_participation(
            self.shift
        )

    def perform_signup(
        self, participant: AbstractParticipant, participation=None, **kwargs
    ) -> AbstractParticipation:
        """
        Creates and/or configures a participation object for a given participant and sends out notifications.
        Passes the participation and kwargs to configure_participation to do configuration specific to the signup method
        """
        from ephios.core.services.notifications.types import ResponsibleParticipationRequested

        if errors := self.get_signup_errors(participant):
            raise ParticipationError(errors)
        participation = participation or self.get_participation_for(participant)
        participation = self._configure_participation(participation, **kwargs)
        participation.save()
        ResponsibleParticipationRequested.send(participation)
        return participation

    def perform_decline(self, participant, participation=None, **kwargs):
        """Create and configure a declining participation object for the given participant. `kwargs` may contain further instructions from a e.g. a form."""
        if errors := self.get_decline_errors(participant):
            raise ParticipationError(errors)
        participation = participation or self.get_participation_for(participant)
        participation.state = AbstractParticipation.States.USER_DECLINED
        participation.save()
        return participation

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        """
        Configure the given participation object for signup according to the method's configuration.
        You need at least to set the participations state. `kwargs` may contain further instructions from e.g. a form.
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
        """
        Return a typle of min, max for how many participants are allowed for the shift.
        Use None for any value if it is not specifiable.
        The default implementation returns None, None to signify both values are not specified.
        """
        return None, None

    def get_signup_stats(self) -> "SignupStats":
        """
        Return an instance of SignupStats for the shift.
        """
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

    def render_shift_state(self, request):
        """
        Render html that will be shown in the shift info box.
        Use it to inform about the current state of the shift and participations.
        """
        return ""

    def get_participation_display(self):
        """
        Returns a displayable representation of participation that can be rendered into a table (e.g. for pdf export).
        Must return a list of participations or empty slots. Each element of the list has to be a list of a fixed
        size where each entry is rendered to a separate column.
        Ex.: [["participant1_name", "participant1_qualification"], ["participant2_name", "participant2_qualification"]]
        """
        return [
            [f"{participant.first_name} {participant.last_name}"]
            for participant in self.shift.get_participants()
        ]

    def get_configuration_form(self, *args, **kwargs):
        if self.shift is not None:
            kwargs.setdefault("initial", self.configuration.__dict__)
        form = self.configuration_form_class(*args, **kwargs)
        return form

    def render_configuration_form(self, *args, form=None, **kwargs):
        form = form or self.get_configuration_form(*args, **kwargs)
        template = Template(
            template_string="{% load crispy_forms_filters %}{{ form|crispy }}"
        ).render(Context({"form": form}))
        return template


@dataclasses.dataclass()
class SignupStats:
    requested_count: int
    confirmed_count: int
    missing: int
    free: Optional[int]  # None means infinite free
    min_count: Optional[int]  # None means no min specified
    max_count: Optional[int]  # None means infinite max

    @classproperty
    def ZERO(cls):  # pylint: disable=no-self-argument
        return SignupStats(
            requested_count=0,
            confirmed_count=0,
            missing=0,
            free=0,
            min_count=None,
            max_count=0,
        )

    def __add__(self, other: "SignupStats"):
        free = self.free + other.free if self.free is not None and other.free is not None else None
        missing = self.missing + other.missing
        min_count = (
            (self.min_count or 0) + (other.min_count or 0)
            if self.min_count is not None or other.min_count is not None
            else None
        )
        max_count = (
            self.max_count + other.max_count
            if self.max_count is not None and other.max_count is not None
            else None
        )
        return SignupStats(
            requested_count=self.requested_count + other.requested_count,
            confirmed_count=self.confirmed_count + other.confirmed_count,
            missing=missing,
            free=free,
            min_count=min_count,
            max_count=max_count,
        )
