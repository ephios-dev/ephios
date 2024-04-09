from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Field, Layout
from django import forms
from django.utils.formats import date_format
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation, Shift
from ephios.core.signup.flow.participant_validation import get_conflicting_participations
from ephios.core.signup.participants import AbstractParticipant
from ephios.extra.widgets import CustomSplitDateTimeWidget


class BaseParticipationForm(forms.ModelForm):
    individual_start_time = forms.SplitDateTimeField(
        label=_("Individual start time"), widget=CustomSplitDateTimeWidget, required=False
    )
    individual_end_time = forms.SplitDateTimeField(
        label=_("Individual end time"),
        widget=CustomSplitDateTimeWidget,
        required=False,
    )

    def clean_individual_start_time(self):
        if self.cleaned_data["individual_start_time"] == self.shift.start_time:
            return None
        return self.cleaned_data["individual_start_time"]

    def clean_individual_end_time(self):
        if self.cleaned_data["individual_end_time"] == self.shift.end_time:
            return None
        return self.cleaned_data["individual_end_time"]

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            start = cleaned_data["individual_start_time"] or self.shift.start_time
            end = cleaned_data["individual_end_time"] or self.shift.end_time
            if end < start:
                self.add_error("individual_end_time", _("End time must not be before start time."))
            return cleaned_data

    class Meta:
        model = AbstractParticipation
        fields = ["individual_start_time", "individual_end_time", "comment"]

    def __init__(self, *args, **kwargs):
        instance = kwargs["instance"]
        kwargs["initial"] = {
            **kwargs.get("initial", {}),
            "individual_start_time": instance.individual_start_time or self.shift.start_time,
            "individual_end_time": instance.individual_end_time or self.shift.end_time,
        }
        super().__init__(*args, **kwargs)

    def get_customization_notification_info(self):
        """
        Return a list of human-readable messages for changed participation attributes responsibles should be informed about.
        This should not include the participation state, but customization aspects such as individual times, detailed disposition information, etc.
        """
        assert self.is_valid()
        info = []
        for time in ["start_time", "end_time"]:
            if (field_name := f"individual_{time}") in self.changed_data:
                info.append(
                    _("{label} was changed from {initial} to {current}.").format(
                        label=self.fields[field_name].label,
                        initial=date_format(
                            localtime(self.initial[field_name].astimezone()),
                            format="SHORT_DATETIME_FORMAT",
                        ),
                        current=date_format(
                            localtime(self.cleaned_data[field_name] or getattr(self.shift, time)),
                            format="TIME_FORMAT",
                        ),
                    )
                )

        return info


class BaseSignupForm(BaseParticipationForm):
    signup_choice = forms.ChoiceField(
        label=_("Signup choice"),
        choices=[
            ("sign_up", _("Sign up")),
            ("customize", _("Customize")),
            ("decline", _("Decline")),
        ],
        widget=forms.HiddenInput,
        required=True,
    )

    def _get_field_layout(self):
        return Layout(*(Field(name) for name in self.fields if name != "signup_choice"))

    def _get_buttons(self):
        if (
            p := self.participant.participation_for(self.shift)
        ) is not None and p.is_in_positive_state():
            buttons = [
                HTML(
                    f'<button class="btn btn-success mt-1 ms-1 float-end" type="submit" name="signup_choice" value="customize">{_("Save")}</button>'
                )
            ]
        else:
            buttons = [
                HTML(
                    f'<button class="btn btn-success mt-1 ms-1 float-end" type="submit" name="signup_choice" value="sign_up">{self.shift.signup_flow.registration_button_text}</button>'
                )
            ]
        buttons.append(
            HTML(
                f'<a class="btn btn-secondary mt-1" href="{self.participant.reverse_event_detail(self.shift.event)}">{_("Cancel")}</a>'
            )
        )
        if self.shift.signup_flow.get_validator(self.participant).can_decline():
            buttons.append(
                HTML(
                    f'<button class="btn btn-secondary mt-1 ms-1 float-end" type="submit" name="signup_choice" value="decline">{_("Decline")}</button>'
                )
            )
        return buttons

    def __init__(self, *args, **kwargs):
        self.shift: Shift = kwargs.pop("shift")
        self.participant: AbstractParticipant = kwargs.pop("participant")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            self._get_field_layout(),
            FormActions(*self._get_buttons()),
        )

        if not getattr(
            self.shift.signup_flow.configuration, "user_can_customize_signup_times", False
        ):
            self.fields["individual_start_time"].disabled = True
            self.fields["individual_end_time"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        self._validate_conflicting_participations()
        return cleaned_data

    def _validate_conflicting_participations(self):
        if self.cleaned_data.get("signup_choice") == "decline":
            return
        if conflicts := get_conflicting_participations(
            participant=self.instance.participant,
            start_time=self.cleaned_data.get("individual_start_time") or self.shift.start_time,
            end_time=self.cleaned_data.get("individual_end_time") or self.shift.end_time,
            shift=self.shift,
            total=False,
        ):
            self.add_error("individual_start_time", "")
            self.add_error(
                "individual_end_time",
                _("You are already confirmed for other shifts at this time: {shifts}.").format(
                    shifts=", ".join(str(shift) for shift in conflicts)
                ),
            )


class SignupConfigurationForm(forms.Form):
    """
    A form class to base signup flow and shift structure configuration forms on.
    """

    template_name = "core/forms/crispy_filter.html"

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop("event")
        self.shift = kwargs.pop("shift")
        self.description = kwargs.pop("description", "")
        super().__init__(*args, **kwargs)
