import typing
from collections import OrderedDict

from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.models import AbstractParticipation, Qualification
from ephios.core.signup import BaseSignupMethod, ParticipationError

_Base = BaseSignupMethod if typing.TYPE_CHECKING else object


class MinMaxParticipantsMixin(_Base):
    @property
    def signup_checkers(self):
        return super().signup_checkers + [self.check_maximum_number_of_participants]

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
        min = self.configuration.minimum_number_of_participants
        max = self.configuration.maximum_number_of_participants
        if min is not None or max is not None:
            if min == max:
                number_info = str(min)
            elif min is not None and max is not None:
                number_info = _("{min} to {max}").format(min=min, max=max)
            elif min is not None:
                number_info = _("at least {min}").format(min=min)
            else:
                number_info = _("at most {max}").format(max=max)
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
        return super().signup_checkers + [self.check_qualification]

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
