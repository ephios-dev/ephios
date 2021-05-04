import typing
from collections import OrderedDict

from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.models import AbstractParticipation, Qualification
from ephios.core.signup import BaseSignupMethod, ParticipationError

_Base = BaseSignupMethod if typing.TYPE_CHECKING else object


class MinMaxParticipantsMixin(_Base):
    @property
    def signup_checkers(self):
        return super()._signup_checkers + [self.check_maximum_number_of_participants]

    @staticmethod
    def check_maximum_number_of_participants(method, participant):
        if (
            not method.uses_requested_state
            and method.configuration.maximum_number_of_participants is not None
        ):
            current_count = AbstractParticipation.objects.filter(
                shift=method.shift, state=AbstractParticipation.States.CONFIRMED
            ).count()
            if current_count >= method.configuration.maximum_number_of_participants:
                return ParticipationError(_("The maximum number of participants is reached."))

    def get_participant_count_bounds(self):
        return (
            self.configuration.minimum_number_of_participants,
            self.configuration.maximum_number_of_participants,
        )

    def get_configuration_fields(self):
        return OrderedDict(
            {
                **super().get_configuration_fields(),
                "minimum_number_of_participants": {
                    "formfield": forms.IntegerField(min_value=0, required=False),
                    "default": None,
                },
                "maximum_number_of_participants": {
                    "formfield": forms.IntegerField(min_value=1, required=False),
                    "default": None,
                },
            }
        )

    def get_signup_info(self):
        infos = super().get_signup_info()
        min_count = self.configuration.minimum_number_of_participants
        max_count = self.configuration.maximum_number_of_participants
        if min_count is not None or max_count is not None:
            if min_count == max_count:
                number_info = str(min_count)
            elif min_count is not None and max_count is not None:
                number_info = _("{min} to {max}").format(min=min_count, max=max_count)
            elif min_count is not None:
                number_info = _("at least {min}").format(min=min_count)
            else:
                number_info = _("at most {max}").format(max=max_count)
            infos.update({_("Required number of participants"): number_info})
        return infos


class QualificationsRequiredSignupMixin(_Base):
    def __init__(self, shift):
        super().__init__(shift)
        if shift is not None:
            self.configuration.required_qualifications = Qualification.objects.filter(
                pk__in=self.configuration.required_qualification_ids
            )

    @property
    def signup_checkers(self):
        return super()._signup_checkers + [self.check_qualification]

    @staticmethod
    def check_qualification(method, participant):
        if not participant.has_qualifications(method.configuration.required_qualifications):
            return ParticipationError(_("You are not qualified."))

    def get_configuration_fields(self):
        return OrderedDict(
            {
                **super().get_configuration_fields(),
                "required_qualification_ids": {
                    "formfield": forms.ModelMultipleChoiceField(
                        label=_("Required Qualifications"),
                        queryset=Qualification.objects.all(),
                        widget=Select2MultipleWidget,
                        required=False,
                    ),
                    "default": [],
                    "publish_with_label": _("Required Qualification"),
                    "format": lambda ids: ", ".join(
                        Qualification.objects.filter(id__in=ids).values_list("title", flat=True)
                    ),
                },
            }
        )

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
