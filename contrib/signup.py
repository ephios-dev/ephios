from django import forms
from django.utils.translation import gettext_lazy as _

from event_management.models import AbstractParticipation
from event_management.signup import AbstractSignupMethod, register_signup_methods, SignupError
from user_management.models import Qualification


class SimpleQualificationsRequiredSignupMethod(AbstractSignupMethod):
    def __init__(self, shift):
        super().__init__(shift)
        if shift is not None:
            self.configuration.required_qualifications = Qualification.objects.filter(
                pk__in=self.configuration.required_qualification_ids
            )

    def get_signup_errors(self, participator):
        errors = super().get_signup_errors(participator)
        if (error := self.check_qualification(participator)) is not None:
            errors.append(error)
        return errors

    def check_qualification(self, participator):
        if not participator.has_qualifications(self.configuration.required_qualifications):
            return SignupError(_("You are not qualified."))

    def get_configuration_fields(self):
        return {
            **super().get_configuration_fields(),
            "required_qualification_ids": {
                "formfield": forms.ModelMultipleChoiceField(
                    label=_("Required Qualifications"), queryset=Qualification.objects.all()
                ),
                "default": [],
            },
        }


class InstantConfirmationSignupMethod(SimpleQualificationsRequiredSignupMethod):
    slug = "instant_confirmation"
    verbose_name = _("Instant Confirmation")
    description = _("""This method instantly confirms a signup.""")

    def get_signup_errors(self, participator):
        errors = super().get_signup_errors(participator)
        if (error := self.check_maximum_number_of_participants()) is not None:
            errors.append(error)
        return errors

    def check_maximum_number_of_participants(self):
        if self.configuration.maximum_number_of_participants is not None:
            current_count = AbstractParticipation.objects.filter(
                shift=self.shift, state=AbstractParticipation.CONFIRMED
            ).count()
            if current_count > self.configuration.maximum_number_of_participants:
                return SignupError(_("The maximum number of participants is reached."))

    def get_configuration_fields(self):
        return {
            **super().get_configuration_fields(),
            "maximum_number_of_participants": {
                "formfield": forms.IntegerField(min_value=1, required=False),
                "default": None,
            },
        }

    def create_participation(self, participator):
        if (participation := participator.participation_for(self.shift)) is None:
            participation = super().create_participation(participator)
        participation.state = AbstractParticipation.CONFIRMED
        participation.save()
        return participation
