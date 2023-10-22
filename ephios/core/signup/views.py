from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.utils.functional import SimpleLazyObject, cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from ephios.core.models import Shift
from ephios.core.services.notifications.types import (
    ResponsibleConfirmedParticipationCustomizedNotification,
)
from ephios.core.signup.checker import BaseSignupMethodError
from ephios.core.signup.forms import BaseSignupForm
from ephios.core.signup.methods import BaseSignupMethod
from ephios.core.signup.participants import AbstractParticipant


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
    signup_success_message = _("You have successfully signed up for {shift}.")
    signup_error_message = _("Signing up failed: {error}")
    decline_success_message = _("You have successfully declined {shift}.")
    decline_error_message = _("Declining failed: {error}")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "method": self.method,
                "participant": self.participant,
                "instance": self.participation,
            }
        )
        return kwargs

    @cached_property
    def participation(self):
        return self.method.get_or_create_participation_for(self.participant)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.participant: AbstractParticipant = kwargs["participant"]
        prevent_getting_participant_from_request_user(request)

    def form_valid(self, form):
        choice = form.cleaned_data["signup_choice"]
        if choice == "sign_up" and self.method.get_validator(self.participant).can_sign_up():
            return self.signup_pressed(form)
        if (
            choice == "customize"
            and self.method.get_validator(self.participant).can_customize_signup()
        ):
            return self.customize_pressed(form)
        if choice == "decline" and self.method.get_validator(self.participant).can_decline():
            return self.decline_pressed(form)
        messages.error(self.request, _("This action is not allowed."))
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def customize_pressed(self, form):
        form.save()
        if claims := form.get_customization_notification_info():
            ResponsibleConfirmedParticipationCustomizedNotification.send(form.instance, claims)
        messages.success(self.request, _("Your participation was saved."))
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def signup_pressed(self, form):
        try:
            with transaction.atomic():
                participation = form.save()
                self.method.perform_signup(self.participant, participation, **form.cleaned_data)
        except BaseSignupMethodError as errors:
            for error in errors:
                messages.error(self.request, self.signup_error_message.format(error=error))
        else:
            messages.success(
                self.request,
                self.signup_success_message.format(shift=self.shift),
            )
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def decline_pressed(self, form):
        try:
            with transaction.atomic():
                participation = form.save()
                self.method.perform_decline(self.participant, participation, **form.cleaned_data)
        except BaseSignupMethodError as errors:
            for error in errors:
                messages.error(self.request, self.decline_error_message.format(error=error))
        else:
            messages.info(self.request, self.decline_success_message.format(shift=self.shift))
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
