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
from ephios.core.signup.flow.participant_validation import BaseSignupError
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

    def get_form_class(self):
        return self.shift.structure.signup_form_class

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

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            form = self.get_form()
            if form.is_valid():
                choice = form.cleaned_data["signup_choice"]
                # select shift for update and get a fresh validator
                validator = (
                    Shift.objects.select_for_update(of=OF_SELF)
                    .prefetch_related("participations")
                    .select_related("event", "event__type")
                    .get(pk=self.shift.pk)
                    .signup_flow.get_validator(self.participant)
                )
                if choice == "sign_up" and validator.can_sign_up():
                    return self.signup_pressed(form)
                if choice == "customize" and validator.can_customize_signup():
                    return self.customize_pressed(form)
                if choice == "decline" and validator.can_decline():
                    return self.decline_pressed(form)
                messages.error(self.request, _("This action is not allowed."))
        return self.form_invalid(form)

    def customize_pressed(self, form):
        form.save()
        if claims := form.get_customization_notification_info():
            ResponsibleConfirmedParticipationCustomizedNotification.send(form.instance, claims)
        messages.success(self.request, _("Your participation was saved."))
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    def signup_pressed(self, form):
        try:
            participation = form.save()
            self.shift.signup_flow.perform_signup(
                self.participant, participation, **form.cleaned_data
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

    def decline_pressed(self, form):
        try:
            participation = form.save()
            self.shift.signup_flow.perform_decline(
                self.participant, participation, **form.cleaned_data
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
