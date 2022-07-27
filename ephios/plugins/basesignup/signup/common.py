import typing

from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.models import AbstractParticipation, Qualification
from ephios.core.signup.methods import (
    BaseSignupMethod,
    ParticipantUnfitError,
    SignupDisallowedError,
)

_Base = BaseSignupMethod if typing.TYPE_CHECKING else object


class MinMaxParticipantsMixin(_Base):
    @property
    def _signup_checkers(self):
        return super()._signup_checkers + [self.check_maximum_number_of_participants]

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
                return SignupDisallowedError(_("The maximum number of participants is reached."))

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
    def _participant_checkers(self):
        return super()._participant_checkers + [self.check_qualification]

    @staticmethod
    def check_qualification(method, participant):
        if not participant.has_qualifications(method.configuration.required_qualifications):
            return ParticipantUnfitError(_("You are not qualified."))

    @property
    def configuration_form_class(self):
        class ConfigurationForm(super().configuration_form_class):
            required_qualification_ids = forms.ModelMultipleChoiceField(
                label=_("Required Qualifications"),
                queryset=Qualification.objects.all(),
                widget=Select2MultipleWidget,
                required=False,
                initial=[],
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
    BaseSignupMethod,
):
    @property
    def slug(self):
        raise NotImplementedError()

    def get_participation_display(self):
        relevant_qualification_categories = global_preferences_registry.manager()[
            "general__relevant_qualification_categories"
        ]
        participation_info = [
            [
                f"{participant.first_name} {participant.last_name}",
                ", ".join(
                    participant.qualifications.filter(
                        category__in=relevant_qualification_categories
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
