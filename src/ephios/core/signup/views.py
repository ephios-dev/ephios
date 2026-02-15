from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.utils.functional import SimpleLazyObject, cached_property
from django.utils.html import format_html
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from ephios.core.models import Shift, UserProfile
from ephios.core.services.notifications.types import (
    ResponsibleConfirmedParticipationCustomizedNotification,
)
from ephios.core.signals import collect_signup_form_fields, signup_save
from ephios.core.signup.flow.participant_validation import (
    BaseSignupError,
    get_conflicting_participations,
)
from ephios.core.signup.forms import SignupForm
from ephios.core.signup.participants import AbstractParticipant, LocalUserParticipant
from ephios.extra.database import OF_SELF


class SignupView(FormView):
    """
    This View reacts to the signup or decline buttons being pressed using a POST request.
    Beware that request.user might be anonymous. You should only act on participants acquired
    using `get_participant`.
    """

    shift: Shift = ...
    template_name = "core/signup.html"
    form_class = SignupForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            "shift": self.shift,
            "participant": self.participant,
            "instance": self.participation,
        })
        return kwargs

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.participant: AbstractParticipant = kwargs["participant"]
        prevent_getting_participant_from_request_user(request)

    @cached_property
    def participation(self):
        return self.shift.signup_flow.get_or_create_participation_for(self.participant)

    def _get_shift_participant_locked_validator(self):
        # We need to avoid race conditions like:
        # - multiple people signing up at the same time violating the max participation count
        # - the user signing up for two conflicting shifts at the same time
        # - there being multiple participation objects for the same participant/shift combination
        # Therefore we select user and shift for update, making transactions block.
        # To avoid Deadlocks, the lock order must always be user, then shift.
        # pylint: disable=protected-access
        if isinstance(self.participant, LocalUserParticipant):
            UserProfile._base_manager.select_for_update(of=OF_SELF).get(pk=self.participant.user.pk)
        return (
            Shift._base_manager
            .select_for_update(of=OF_SELF)
            .prefetch_related("participations")
            .select_related("event", "event__type")
            .get(pk=self.shift.pk)
        ).signup_flow.get_validator(self.participant)

    def _collect_quick_action_signup_data(self):
        """
        Collect defaults for the signup fields to use instead of cleaned_data from a SignupForm.
        Returns None and adds messages to the request if conditions don't allow providing this data
        without explicit user input.
        """
        signup_choice = self.request.POST.get("signup_choice")
        data = {
            "signup_choice": signup_choice,  # validated later
            "individual_start_time": self.participation.individual_start_time
            or self.shift.start_time,
            "individual_end_time": self.participation.individual_end_time or self.shift.end_time,
        }
        if signup_choice != SignupForm.SignupChoices.DECLINE and (
            conflicts := get_conflicting_participations(
                participant=self.participant,
                # intentionally use the original shift times here (ignoring individual times on quick_signup)
                # so participants are forced to recheck their individual times (except when declining)
                start_time=self.shift.start_time,
                end_time=self.shift.end_time,
                shift=self.shift,
                total=False,
            )
        ):
            messages.warning(
                self.request,
                format_html(
                    gettext(
                        "Please check that your individual start and end times do not overlap with these "
                        "other confirmed participations: {shifts}"
                    ),
                    shifts=", ".join(str(shift) for shift in conflicts),
                ),
            )
            return None

        for fieldname, field in collect_signup_form_fields(
            self.shift, self.participant, self.participation, signup_choice
        ):
            if field["required"] and not field["default"]:
                # not supported by quick action
                messages.info(
                    self.request,
                    _("We need some additional information to sign you up for this shift."),
                )
                return None
            data[fieldname] = field["default"]
        return data

    def post(self, request, *args, **kwargs):
        if request.POST.get("quick_action"):
            if not (signup_data := self._collect_quick_action_signup_data()):
                # quick action not valid -> redirect so it acts like a click on the customize-button
                return redirect(self.participant.reverse_signup_action(self.shift))
            try:
                instance = self.participation
                with transaction.atomic():
                    validator = self._get_shift_participant_locked_validator()
                    instance.save()
                    return self._process_signup_action(instance, signup_data, validator)
            except BaseSignupError:
                return redirect(self.participant.reverse_event_detail(self.shift.event))

        # deal with a regular SignupForm submit
        try:
            form = self.get_form()
            if form.is_valid():
                signup_data = form.cleaned_data
                with transaction.atomic():
                    validator = self._get_shift_participant_locked_validator()
                    instance = form.save()
                    if signup_data["signup_choice"] == SignupForm.SignupChoices.CUSTOMIZE and (
                        claims := form.get_customization_notification_info()
                    ):
                        ResponsibleConfirmedParticipationCustomizedNotification.send(
                            form.instance, claims
                        )
                    return self._process_signup_action(instance, signup_data, validator)
        except BaseSignupError:
            # jump back to event-detail, in case SignupForm should be unreachable
            return redirect(self.participant.reverse_event_detail(self.shift.event))
        return self.form_invalid(form)

    def _process_signup_action(self, participation, signup_data, validator):
        match signup_data["signup_choice"]:
            case SignupForm.SignupChoices.SIGNUP if validator.can_sign_up():
                flow_action = self.shift.signup_flow.perform_signup
                error_message = self.shift.signup_flow.signup_error_message
                success_message = self.shift.signup_flow.signup_success_message
            case SignupForm.SignupChoices.DECLINE if validator.can_decline():
                flow_action = self.shift.signup_flow.perform_decline
                error_message = self.shift.signup_flow.decline_error_message
                success_message = self.shift.signup_flow.decline_success_message
            case SignupForm.SignupChoices.CUSTOMIZE if validator.can_customize_signup():
                # pylint: disable-next=unnecessary-lambda-assignment
                flow_action = lambda **kwargs: None  # noop  # noqa
                error_message = _("There was an error saving your participation.")
                success_message = _("Your participation was saved.")
            case _:
                messages.error(self.request, _("This action is not allowed."))
                raise BaseSignupError(_("This action is not allowed."))
        try:
            self._send_signup_save_signal(participation, signup_data)
            flow_action(
                participant=self.participant,
                participation=participation,
                acting_user=self._acting_user,
                **signup_data,
            )
        except BaseSignupError as error:
            # except hook for inserting the error message
            messages.error(self.request, error_message.format(error=error))
            raise  # must reraise for transaction rollback
        messages.success(self.request, success_message.format(shift=self.shift))
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def _send_signup_save_signal(self, participation, signup_data):
        signup_save.send(
            sender=None,
            shift=self.shift,
            participant=self.participant,
            participation=participation,
            signup_choice=signup_data["signup_choice"],
            cleaned_data=signup_data,
        )

    @property
    def _acting_user(self):
        if self.request.user.is_authenticated:
            return self.request.user
        # Anonymous users are handled as None, they can't be serialized
        # to JSON down the Notification data road. Wouldn't be of use anyway.
        return None


def prevent_getting_participant_from_request_user(request):
    """
    To prevent plugin authors from accessing the participant using request.user, the SignupView
    uses this method to block access to `as_participant` of the request.user attribute value.
    """
    original_user = request.user

    class ProtectedUser(SimpleLazyObject):
        def as_participant(self):
            raise AttributeError(
                "Access of request.user.as_participant in SignupViews is not allowed."
            )

    request.user = ProtectedUser(lambda: original_user)
