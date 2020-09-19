from django import forms
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from event_management.models import AbstractParticipation
from event_management.signup import (
    BaseSignupMethod,
    register_signup_methods,
    ParticipationError,
)
from user_management.models import Qualification


class SimpleQualificationsRequiredSignupMethod(BaseSignupMethod):
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
    def check_qualification(method, participator):
        if not participator.has_qualifications(method.configuration.required_qualifications):
            return ParticipationError(_("You are not qualified."))

    def get_configuration_fields(self):
        return {
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


class InstantConfirmationSignupMethod(SimpleQualificationsRequiredSignupMethod):
    slug = "instant_confirmation"
    verbose_name = _("Instant Confirmation")
    description = _("""This method instantly confirms a signup.""")

    @property
    def signup_checkers(self):
        return super().signup_checkers + [self.check_maximum_number_of_participants]

    @staticmethod
    def check_maximum_number_of_participants(method, participator):
        if method.configuration.maximum_number_of_participants is not None:
            current_count = AbstractParticipation.objects.filter(
                shift=method.shift, state=AbstractParticipation.States.CONFIRMED
            ).count()
            if current_count >= method.configuration.maximum_number_of_participants:
                return ParticipationError(_("The maximum number of participants is reached."))

    def get_configuration_fields(self):
        return {
            **super().get_configuration_fields(),
            "maximum_number_of_participants": {
                "formfield": forms.IntegerField(min_value=1, required=False),
                "default": None,
                "publish_with_label": _("Maximum number of participants"),
            },
        }

    def render_shift_state(self, request):
        return get_template("jepcontrib/signup_instant_state.html").render({"shift": self.shift})

    def perform_signup(self, participator, **kwargs):
        participation = super().perform_signup(participator, **kwargs)
        participation.state = AbstractParticipation.States.CONFIRMED
        participation.save()
        return participation
