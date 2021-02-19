from django import forms
from django.utils.translation import gettext_lazy as _
from django_select2.forms import Select2MultipleWidget

from ephios.core.models import Qualification
from ephios.core.signup import BaseSignupMethod, ParticipationError


class SimpleQualificationsRequiredSignupMethod(BaseSignupMethod):
    # pylint: disable=abstract-method
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
