from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.utils.functional import SimpleLazyObject, cached_property
from django.utils.translation import gettext_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from ephios.core.models import Shift
from ephios.core.services.notifications.types import (
    ResponsibleConfirmedParticipationCustomizedNotification,
)
from ephios.core.signals import signup_form_fields, signup_save
from ephios.core.signup.flow.participant_validation import (
    BaseSignupError,
    get_conflicting_participations,
)
from ephios.core.signup.forms import SignupForm
from ephios.core.signup.participants import AbstractParticipant
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
        kwargs.update(
            {
                "shift": self.shift,
                "participant": self.participant,
                "instance": self.participation,
            }
        )
        return kwargs

    @cached_property
    def participation(self):
        return self.shift.signup_flow.get_or_create_participation_for(self.participant)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.participant: AbstractParticipant = kwargs["participant"]
        prevent_getting_participant_from_request_user(request)

    def _collect_quick_action_signup_data(self):
        signup_choice = self.request.POST.get("signup_choice")
        data = {
            "signup_choice": signup_choice,  # validated later
            "individual_start_time": self.shift.start_time,
            "individual_end_time": self.shift.end_time,
        }
        if signup_choice != "decline" and (
            conflicts := get_conflicting_participations(
                participant=self.participant,
                start_time=self.shift.start_time,
                end_time=self.shift.end_time,
                shift=self.shift,
                total=False,
            )
        ):
            messages.warning(
                self.request,
                gettext_lazy(
                    "You are already confirmed for other shifts at this time: {shifts}. Please adjust the timing."
                ).format(shifts=", ".join(str(shift) for shift in conflicts)),
            )
            return None
        responses = signup_form_fields.send(
            sender=None,
            shift=self.shift,
            participant=self.participant,
            participation=self.participation,
            signup_choice=signup_choice,
        )
        for _, additional_fields in responses:
            for fieldname, field in additional_fields.items():
                if field["required"] and not field["default"]:
                    # not supported by quick action
                    messages.warning(
                        self.request, gettext_lazy("Some fields are required for signup.")
                    )
                    return None
                data[fieldname] = field["default"]
        return data

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if request.POST.get("quick_action"):
            instance = self.participation
            if not (signup_data := self._collect_quick_action_signup_data()):
                # quick action not valid -> redirect so it acts like a click on the customize button
                return redirect(self.participant.reverse_signup_action(self.shift))
            with transaction.atomic():
                instance.save()
                return self._process_signup_action(instance, signup_data)
        else:
            if not form.is_valid():
                return self.form_invalid(form)
            signup_data = form.cleaned_data
            with transaction.atomic():
                instance = form.save()
                if claims := form.get_customization_notification_info():
                    ResponsibleConfirmedParticipationCustomizedNotification.send(
                        form.instance, claims
                    )
                return self._process_signup_action(instance, signup_data)

    def _process_signup_action(self, participation, signup_data):
        # select shift for update and get a fresh validator
        validator = (
            Shift.objects.select_for_update(of=OF_SELF)
            .prefetch_related("participations")
            .select_related("event", "event__type")
            .get(pk=self.shift.pk)
            .signup_flow.get_validator(self.participant)
        )
        if (
            signup_data["signup_choice"] == SignupForm.SignupChoices.SIGNUP
            and validator.can_sign_up()
        ):
            return self.signup_pressed(participation, signup_data)
        if (
            signup_data["signup_choice"] == SignupForm.SignupChoices.CUSTOMIZE
            and validator.can_customize_signup()
        ):
            return self.customize_pressed(participation, signup_data)
        if (
            signup_data["signup_choice"] == SignupForm.SignupChoices.DECLINE
            and validator.can_decline()
        ):
            return self.decline_pressed(participation, signup_data)
        messages.error(self.request, _("This action is not allowed."))
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def customize_pressed(self, participation, signup_data):
        signup_save.send(
            sender=None,
            shift=self.shift,
            participant=self.participant,
            participation=participation,
            signup_choice=signup_data["signup_choice"],
            cleaned_data=signup_data,
        )
        messages.success(self.request, _("Your participation was saved."))
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    @property
    def _acting_user(self):
        if self.request.user.is_authenticated:
            return self.request.user
        # Anonymous users are handled as None, they can't be serialized
        # to JSON down the Notification data road. Wouldn't be of use anyway.
        return None

    def signup_pressed(self, participation, signup_data):
        try:
            signup_save.send(
                sender=None,
                shift=self.shift,
                participant=self.participant,
                participation=participation,
                signup_choice=signup_data["signup_choice"],
                cleaned_data=signup_data,
            )
            self.shift.signup_flow.perform_signup(
                participant=self.participant,
                participation=participation,
                acting_user=self._acting_user,
                **signup_data,
            )
        except BaseSignupError as errors:
            for error in errors:  # pylint:disable=not-an-iterable
                messages.error(
                    self.request, self.shift.signup_flow.signup_error_message.format(error=error)
                )
        else:
            messages.success(
                self.request,
                self.shift.signup_flow.signup_success_message.format(shift=self.shift),
            )
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def decline_pressed(self, participation, signup_data):
        try:
            signup_save.send(
                sender=None,
                shift=self.shift,
                participant=self.participant,
                participation=participation,
                signup_choice=signup_data["signup_choice"],
                cleaned_data=signup_data,
            )
            self.shift.signup_flow.perform_decline(
                participant=self.participant,
                participation=participation,
                acting_user=self._acting_user,
                **signup_data,
            )
        except BaseSignupError as errors:
            for error in errors:  # pylint:disable=not-an-iterable
                messages.error(
                    self.request, self.shift.signup_flow.decline_error_message.format(error=error)
                )
        else:
            messages.info(
                self.request,
                self.shift.signup_flow.decline_success_message.format(shift=self.shift),
            )
        return redirect(self.participant.reverse_event_detail(self.shift.event))


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
