import typing

from django import forms
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.models import AbstractParticipation, Qualification
from ephios.core.signup.checker import (
    ActionDisallowedError,
    BaseSignupActionValidator,
    ParticipantUnfitError,
    SignupDisallowedError,
)
from ephios.core.signup.methods import BaseSignupMethod
from ephios.core.signup.views import BaseSignupView

_Base = BaseSignupMethod if typing.TYPE_CHECKING else object


class MinimumAgeConfigFormMixin(forms.Form):
    minimum_age = forms.IntegerField(
        required=False, min_value=0, max_value=999, initial=None, label=_("Minimum age")
    )


class MinimumAgeMixin(_Base):
    @property
    def signup_action_validator_class(self):
        class Validator(super().signup_action_validator_class):
            @staticmethod
            def check_participant_age(method, participant):
                minimum_age = getattr(method.configuration, "minimum_age", None)
                day = method.shift.start_time.date()
                age = participant.get_age(day)
                if minimum_age is not None and age is not None and age < minimum_age:
                    raise ParticipantUnfitError(
                        _("You are too young. The minimum age is {age}.").format(age=minimum_age)
                    )

            def get_checkers(self):
                return super().get_checkers() + [self.check_participant_age]

        return Validator

    @property
    def configuration_form_class(self):
        class ConfigurationForm(MinimumAgeConfigFormMixin, super().configuration_form_class):
            pass

        return ConfigurationForm


class MinMaxParticipantsMixin(_Base):
    @property
    def signup_action_validator_class(self):
        class Validator(super().signup_action_validator_class):
            @staticmethod
            def check_maximum_number_of_participants(method, participant):
                if (
                    not method.uses_requested_state
                    and method.configuration.maximum_number_of_participants is not None
                ):
                    current_count = len(
                        [
                            participation
                            for participation in method.shift.participations.all()
                            if participation.state == AbstractParticipation.States.CONFIRMED
                        ]
                    )
                    if current_count >= method.configuration.maximum_number_of_participants:
                        raise SignupDisallowedError(
                            _("The maximum number of participants is reached.")
                        )

            def get_checkers(self):
                return super().get_checkers() + [self.check_maximum_number_of_participants]

        return Validator

    def get_participant_count_bounds(self):
        return (
            self.configuration.minimum_number_of_participants,
            self.configuration.maximum_number_of_participants,
        )

    @property
    def configuration_form_class(self):
        class ConfigurationForm(super().configuration_form_class):
            minimum_number_of_participants = forms.IntegerField(
                label=_("Minimum number of participants"), min_value=0, required=False
            )
            maximum_number_of_participants = forms.IntegerField(
                label=_("Maximum number of participants"), min_value=1, required=False
            )

        return ConfigurationForm

    def get_shift_state_context_data(self, request, **kwargs):
        context_data = super().get_shift_state_context_data(request, **kwargs)
        context_data["empty_spots"] = range(
            max(
                0,
                (getattr(self.configuration, "minimum_number_of_participants", None) or 0)
                - len(context_data["participations"]),
            )
        )
        return context_data


class QualificationsRequiredSignupMixin(_Base):
    def __init__(self, shift, **kwargs):
        super().__init__(shift, **kwargs)
        if shift is not None:
            self.configuration.required_qualifications = Qualification.objects.filter(
                pk__in=self.configuration.required_qualification_ids
            )

    @property
    def signup_action_validator_class(self):
        class Validator(super().signup_action_validator_class):
            @staticmethod
            def check_qualification(method, participant):
                if not participant.has_qualifications(method.configuration.required_qualifications):
                    raise ParticipantUnfitError(
                        _("You don't have all required qualifications for this shift.")
                    )

            def get_checkers(self):
                return super().get_checkers() + [self.check_qualification]

        return Validator

    @property
    def configuration_form_class(self):
        class ConfigurationForm(super().configuration_form_class):
            required_qualification_ids = forms.ModelMultipleChoiceField(
                label=_("Required Qualifications"),
                queryset=Qualification.objects.all(),
                widget=Select2MultipleWidget,
                required=False,
                initial=[],
                help_text=_(
                    "Participants also need to have the qualifications <b>{qualifications}</b> to participate in {eventtype}"
                ).format(
                    qualifications=",".join(
                        self.event.type.preferences.get("general_required_qualifications")
                        .all()
                        .values_list("title", flat=True)
                    ),
                    eventtype=self.event.type,
                )
                if self.event.type.preferences.get("general_required_qualifications").exists()
                else None,
            )

            @staticmethod
            def format_required_qualification_ids(ids):
                return ", ".join(
                    Qualification.objects.filter(id__in=ids).values_list("title", flat=True)
                )

        return ConfigurationForm

    def get_shift_state_context_data(self, request, **kwargs):
        return super().get_shift_state_context_data(
            request,
            **kwargs,
            required_qualification=", ".join(
                q.abbreviation for q in self.configuration.required_qualifications
            ),
        )


class RenderParticipationPillsShiftStateMixin:
    shift_state_template_name = "basesignup/fragment_participation_pills_shift_state.html"


class QualificationMinMaxBaseSignupMethod(
    RenderParticipationPillsShiftStateMixin,
    QualificationsRequiredSignupMixin,
    MinMaxParticipantsMixin,
    MinimumAgeMixin,
    BaseSignupMethod,
):
    @property
    def slug(self):
        raise NotImplementedError()

    def get_participation_display(self):
        participation_info = [
            [
                participant.display_name,
                ", ".join(
                    participant.qualifications.filter(
                        category__show_with_user=True,
                    )
                    .order_by("category", "title")
                    .values_list("title", flat=True)
                ),
            ]
            for participant in self.shift.get_participants()
        ]
        min_count, max_count = self.get_participant_count_bounds()
        rendered_count = max(min_count or 0, max_count or 0)
        if len(participation_info) < rendered_count:
            required_qualifications = self.configuration.required_qualifications
            qualifications_display = (
                ", ".join(required_qualifications.values_list("title", flat=True))
                if required_qualifications
                else "-"
            )
            participation_info += [["", qualifications_display]] * (
                rendered_count - len(participation_info)
            )
        return participation_info


class NoSignupSignupView(BaseSignupView):
    def get(self, request, *args, **kwargs):
        messages.error(self.request, _("This action is not allowed."))
        return redirect(self.participant.reverse_event_detail(self.shift.event))

    post = get


class NoSignupSignupActionValidator(BaseSignupActionValidator):
    def get_no_signup_allowed_message(self):
        return _("Signup for this shift is disabled.")

    def signup_is_disabled(self, method, participant):
        raise ActionDisallowedError(self.get_no_signup_allowed_message())

    def get_checkers(self):
        return [self.signup_is_disabled]
