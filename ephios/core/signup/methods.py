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
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.functional import SimpleLazyObject, cached_property, classproperty
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from ephios.core.models import AbstractParticipation, Shift
from ephios.core.services.notifications.types import (
    ResponsibleConfirmedParticipationCustomizedNotification,
    ResponsibleConfirmedParticipationDeclinedNotification,
)
from ephios.core.signals import (
    check_participant_signup,
    participant_from_request,
    register_signup_methods,
)
from ephios.core.signup.participants import AbstractParticipant
from ephios.extra.utils import format_anything
from ephios.extra.widgets import CustomSplitDateTimeWidget

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
    """Superclass of errors used in the signup mechanism."""


class ActionDisallowedError(ValidationError):
    """Error to return if the participant cannot perform an action on a shift."""


class SignupDisallowedError(ActionDisallowedError):
    """
    Error to return if the participant cannot sign up for a shift,
    even if formally fit, because of certain other circumstances.
    """


class DeclineDisallowedError(ActionDisallowedError):
    """Error to return if the participant cannot decline a shift."""


class ParticipantUnfitError(ParticipationError):
    """
    Error to return if the participant is unfit for a shift,
    regardless of participation state or situation.
    """


class ImproperlyConfiguredError(ParticipationError):
    """
    Error to return if signup cannot be performed for
    technical or configuration reasons.
    """


def prevent_getting_participant_from_request_user(request):
    """
    To prevent plugin authors from accessing the participant using request.user, the SignupView
    uses this method to block access to `as_participant` of the request.user attribute value.
    """
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

    def clean_individual_start_time(self):
        if self.cleaned_data["individual_start_time"] == self.shift.start_time:
            return None
        return self.cleaned_data["individual_start_time"]

    def clean_individual_end_time(self):
        if self.cleaned_data["individual_end_time"] == self.shift.end_time:
            return None
        return self.cleaned_data["individual_end_time"]

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data["individual_start_time"] or self.shift.start_time
        end = cleaned_data["individual_end_time"] or self.shift.end_time
        if end < start:
            self.add_error("individual_end_time", _("End time must not be before start time."))
        return cleaned_data

    class Meta:
        model = AbstractParticipation
        fields = ["individual_start_time", "individual_end_time", "comment"]

    def __init__(self, *args, **kwargs):
        instance = kwargs["instance"]
        kwargs["initial"] = {
            **kwargs.get("initial", {}),
            "individual_start_time": instance.individual_start_time or self.shift.start_time,
            "individual_end_time": instance.individual_end_time or self.shift.end_time,
        }
        super().__init__(*args, **kwargs)

    def get_customization_notification_info(self):
        """
        Return a list of human readable messages for changed participation attributes responsibles should be informed about.
        This should not include the participation state, but customization aspects such as individual times, detailed disposition information, etc.
        """
        assert self.is_valid()
        info = []
        for time in ["start_time", "end_time"]:
            if (field_name := f"individual_{time}") in self.changed_data:
                info.append(
                    _("{label} was changed from {initial} to {current}.").format(
                        label=self.fields[field_name].label,
                        initial=date_format(
                            localtime(self.initial[field_name].astimezone()),
                            format="SHORT_DATETIME_FORMAT",
                        ),
                        current=date_format(
                            localtime(self.cleaned_data[field_name] or getattr(self.shift, time)),
                            format="TIME_FORMAT",
                        ),
                    )
                )

        return info


class BaseSignupForm(BaseParticipationForm):
    def _get_field_layout(self):
        return Layout(*(Field(name) for name in self.fields))

    def _get_buttons(self):
        if (
            p := self.participant.participation_for(self.method.shift)
        ) is not None and p.is_in_positive_state():
            buttons = [
                HTML(
                    f'<button class="btn btn-success mt-1 ms-1 float-end" type="submit" name="signup_choice" value="customize">{_("Save")}</button>'
                )
            ]
        else:
            buttons = [
                HTML(
                    f'<button class="btn btn-success mt-1 ms-1 float-end" type="submit" name="signup_choice" value="sign_up">{self.method.registration_button_text}</button>'
                )
            ]
        buttons.append(
            HTML(
                f'<a class="btn btn-secondary mt-1" href="{self.participant.reverse_event_detail(self.method.shift.event)}">{_("Cancel")}</a>'
            )
        )
        if self.method.can_decline(self.participant):
            buttons.append(
                HTML(
                    f'<button class="btn btn-secondary mt-1 ms-1 float-end" type="submit" name="signup_choice" value="decline">{_("Decline")}</button>'
                )
            )
        return buttons

    def __init__(self, *args, **kwargs):
        self.method = kwargs.pop("method")
        self.targets_positive_state = kwargs.pop("targets_positive_state")
        self.shift: Shift = self.method.shift
        self.participant: AbstractParticipant = kwargs.pop("participant")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            self._get_field_layout(),
            FormActions(*self._get_buttons()),
        )

        if not self.shift.signup_method.configuration.user_can_customize_signup_times:
            self.fields["individual_start_time"].disabled = True
            self.fields["individual_end_time"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        self._validate_conflicting_participations(self, self.targets_positive_state)
        return cleaned_data

    def _validate_conflicting_participations(self, form, targets_positive_state):
        if not targets_positive_state:
            return
        if conflicts := get_conflicting_participations(
            participant=form.instance.participant,
            start_time=form.cleaned_data["individual_start_time"] or self.shift.start_time,
            end_time=form.cleaned_data["individual_end_time"] or self.shift.end_time,
            shift=self.shift,
            total=False,
        ):
            form.add_error("individual_start_time", "")
            form.add_error(
                "individual_end_time",
                _("You are already confirmed for other shifts at this time: {shifts}.").format(
                    shifts=", ".join(str(shift) for shift in conflicts)
                ),
            )


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
                "instance": self.participation,
                "targets_positive_state": self.request.POST.get("signup_choice") == "sign_up",
            }
        )
        return kwargs

    @cached_property
    def participation(self):
        return self.method.get_participation_for(self.participant)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.participant: AbstractParticipant = kwargs["participant"]
        prevent_getting_participant_from_request_user(request)

    def form_valid(self, form):
        if (choice := self.request.POST.get("signup_choice")) is not None:
            if choice == "sign_up" and self.method.can_sign_up(self.participant):
                return self.signup_pressed(form)
            if choice == "customize" and self.method.can_customize_signup(self.participant):
                return self.customize_pressed(form)
            if choice == "decline":
                return self.decline_pressed(form)
            messages.error(self.request, _("This action is not allowed."))
            return redirect(self.participant.reverse_event_detail(self.shift.event))
        form.add_error(None, _("Form submission is missing the mode of signup."))
        return self.form_invalid(form)

    def customize_pressed(self, form):
        form.save()
        if claims := form.get_customization_notification_info():
            ResponsibleConfirmedParticipationCustomizedNotification(form.instance, claims).send()
        messages.success(self.request, _("Your participation was saved."))
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def signup_pressed(self, form):
        try:
            with transaction.atomic():
                participation = form.save()
                self.method.perform_signup(self.participant, participation, **form.cleaned_data)
        except ParticipationError as errors:
            for error in errors:
                messages.error(self.request, self.method.signup_error_message.format(error=error))
        else:
            messages.success(
                self.request,
                self.method.signup_success_message.format(shift=self.shift),
            )
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def decline_pressed(self, form):
        try:
            with transaction.atomic():
                participation = form.save()
                self.method.perform_decline(self.participant, participation, **form.cleaned_data)
        except ParticipationError as errors:
            for error in errors:
                messages.error(self.request, self.method.decline_error_message.format(error=error))
        else:
            messages.info(
                self.request, self.method.decline_success_message.format(shift=self.shift)
            )
        return redirect(self.participant.reverse_event_detail(self.shift.event))


def check_event_is_active(method, participant):
    if not method.shift.event.active:
        return ActionDisallowedError(_("The event is not active."))


def check_participation_state_for_signup(method, participant):
    participation = participant.participation_for(method.shift)
    if participation is not None:
        if participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
            return SignupDisallowedError(_("You have been rejected."))


def check_participation_state_for_decline(method, participant):
    participation = participant.participation_for(method.shift)
    if participation is not None:
        if (
            participation.state == AbstractParticipation.States.CONFIRMED
            and not method.configuration.user_can_decline_confirmed
        ):
            return DeclineDisallowedError(_("You cannot decline by yourself."))
        if participation.state == AbstractParticipation.States.RESPONSIBLE_REJECTED:
            return DeclineDisallowedError(_("You have been rejected."))
        if participation.state == AbstractParticipation.States.USER_DECLINED:
            return DeclineDisallowedError(_("You have already declined participating."))


def check_inside_signup_timeframe(method, participant):
    last_time = method.shift.end_time
    if method.configuration.signup_until is not None:
        last_time = min(last_time, method.configuration.signup_until)
    if timezone.now() > last_time:
        return ActionDisallowedError(_("The signup period is over."))


def check_participant_age(method, participant):
    minimum_age = method.configuration.minimum_age
    day = method.shift.start_time.date()
    age = participant.get_age(day)
    if minimum_age is not None and age is not None and age < minimum_age:
        return ParticipantUnfitError(
            _("You are too young. The minimum age is {age}.").format(age=minimum_age)
        )


def check_participant_signup_signal(method, participant):
    errors = []
    for _, result in check_participant_signup.send(None, method=method, participant=participant):
        if result is not None:
            errors.append(result)
    return errors


def get_conflicting_participations(
    participant: AbstractParticipant, shift: Shift, start_time=None, end_time=None, total=False
):
    """
    Return a queryset of participations of a participant in conflict with
    a (potential) participation specified by the arguments.

        Parameters:
            participant: AbstractParticipant to check conflict for
            shift: conflicting participations for this shift
            start_time, end_time: specify times other than the default times of `shift`
            total (bool): If True, only return conflicts that can't be
                          resolved by only participating in only part of `shift`.

        Returns:
            a queryset of participations
    """
    start_time = start_time or shift.start_time
    end_time = end_time or shift.end_time
    qs = participant.all_participations().filter(
        ~Q(shift=shift)
        & Q(state=AbstractParticipation.States.CONFIRMED)
        & Q(start_time__lt=end_time, end_time__gt=start_time)
    )
    if total:
        qs = qs.filter(start_time__lte=shift.start_time, end_time__gte=shift.end_time)
    return qs


def check_conflicting_participations(method, participant):
    start_time, end_time = method.shift.start_time, method.shift.end_time
    if participation := participant.participation_for(method.shift):
        start_time, end_time = participation.start_time, participation.end_time

    # if users can provide individual times, only total conflicts should block signup
    total = getattr(method.configuration, "user_can_customize_signup_times", False)
    if conflicts := get_conflicting_participations(
        participant=participant,
        shift=method.shift,
        start_time=start_time,
        end_time=end_time,
        total=total,
    ):
        return SignupDisallowedError(
            _("You are already confirmed for other shifts at this time: {shifts}.").format(
                shifts=", ".join(str(shift) for shift in conflicts)
            )
        )


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

    @property
    def shift_state_template_name(self):
        raise NotImplementedError

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
        """Return a list of methods that check if the participant can sign up for the shift."""
        return [
            check_event_is_active,
            check_participation_state_for_signup,
            check_inside_signup_timeframe,
            check_conflicting_participations,
            check_participant_age,
            check_participant_signup_signal,
        ]

    @property
    def _decline_checkers(self):
        """Return a list of methods that check if the participant can decline the shift."""
        return [
            check_event_is_active,
            check_participation_state_for_decline,
            check_inside_signup_timeframe,
        ]

    def _run_checkers(self, participant, checkers) -> List[ParticipationError]:
        errors = []
        for checker in checkers:
            # checkers can return None, a single ParticipationError, or a list of them
            if (error := checker(self, participant)) is not None:
                if isinstance(error, list):
                    errors.extend(error)
                else:
                    errors.append(error)
        return errors

    @functools.lru_cache(maxsize=64)
    def get_signup_errors(self, participant) -> List[ParticipationError]:
        """Return a list of ParticipationErrors that describe reasons for not being able to sign up."""
        return self._run_checkers(participant, self._signup_checkers)

    @functools.lru_cache(maxsize=64)
    def get_decline_errors(self, participant):
        """Return a list of ParticipationErrors that describe reasons for not being able to decline."""
        return self._run_checkers(participant, self._decline_checkers)

    def get_participant_errors(self, participant) -> List[ParticipationError]:
        """
        Return errors for whether the participant fulfills the requirements set by the signup methods for participation.
        This runs a subset of the check for `get_signup_errors`.
        """
        return list(
            filter(
                lambda error: isinstance(error, ParticipantUnfitError),
                self.get_signup_errors(participant),
            )
        )

    def can_decline(self, participant):
        """
        Return whether the participant is allowed to decline.
        """
        return not self.get_decline_errors(participant)

    def can_sign_up(self, participant):
        """
        Return whether the participant is allowed to perform signup.
        """
        signupable_state = (
            p := participant.participation_for(self.shift)
        ) is None or not p.is_in_positive_state()
        return signupable_state and not self.get_signup_errors(participant)

    def can_customize_signup(self, participant):
        """
        Return whether the participant gets shown the option to customize their participation.
        """
        positive_state = (
            p := participant.participation_for(self.shift)
        ) is not None and p.is_in_positive_state()

        if positive_state:
            # If in positive state, check that you can decline and then sign up again.
            return self.can_decline(participant) and not self.get_signup_errors(participant)
        return not self.get_signup_errors(participant)

    def has_customized_signup(self, participation):
        """
        Return whether the participation was customized in a way specific to this signup method.
        """
        # This method should most likely check the participation's data attribute for modifications it has done.
        # 'Customized' in this context means that the dispositioning person should give special attention to this participation.
        return False

    def get_participation_for(self, participant) -> AbstractParticipation:
        return participant.participation_for(self.shift) or participant.new_participation(
            self.shift
        )

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

        if errors := self.get_signup_errors(participant):
            raise ParticipationError(errors)
        participation = participation or self.get_participation_for(participant)
        participation = self._configure_participation(participation, **kwargs)
        participation.save()
        ResponsibleParticipationRequestedNotification(participation).send()
        return participation

    def perform_decline(self, participant, participation=None, **kwargs):
        """Create and configure a declining participation object for the given participant. `kwargs` may contain further instructions from a e.g. a form."""
        if errors := self.get_decline_errors(participant):
            raise ParticipationError(errors)
        participation = participation or self.get_participation_for(participant)
        participation.state = AbstractParticipation.States.USER_DECLINED
        participation.save()
        ResponsibleConfirmedParticipationDeclinedNotification(participation).send()
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

    def render(self, context):
        """
        Render the state/participations of the shift.
        Match the signature of template.render for use with the include template tag:
        {% include shift.signup_method %}
        By default, this loads `shift_state_template_name` and renders it using context from `get_shift_state_context_data`.
        """
        try:
            with context.update(self.get_shift_state_context_data(context.request)):
                return get_template(self.shift_state_template_name).template.render(context)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Shift #{self.shift.pk} state render failed")
            with context.update(dict(exception_message=getattr(e, "message", None))):
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
                reverse("core:shift_disposition", kwargs=dict(pk=self.shift.pk))
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


@dataclasses.dataclass(frozen=True)
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
