from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Field, Layout
from django import forms
from django.db import models, transaction
from django.utils.formats import date_format
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation, Shift
from ephios.core.models.events import ParticipationComment
from ephios.core.signals import collect_signup_form_fields
from ephios.core.signup.flow.participant_validation import get_conflicting_participations
from ephios.core.signup.participants import AbstractParticipant
from ephios.core.widgets import PreviousCommentWidget
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
    comment = forms.CharField(label=_("Comment"), max_length=255, required=False, label_suffix="")
    comment_is_public = forms.BooleanField(
        label=_("Make comment visible for other participants"), required=False, label_suffix=""
    )

    def clean_individual_start_time(self):
        if self.cleaned_data["individual_start_time"] == self.shift.start_time:
            return None
        return self.cleaned_data["individual_start_time"]

    def clean_individual_end_time(self):
        if self.cleaned_data["individual_end_time"] == self.shift.end_time:
            return None
        return self.cleaned_data["individual_end_time"]

    def get_comment_visibility(self):
        return (
            ParticipationComment.Visibility.PUBLIC
            if self.cleaned_data["comment_is_public"]
            else ParticipationComment.Visibility.PARTICIPANT
        )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["comment_visibility"] = self.get_comment_visibility()
        if not self.errors:
            start = cleaned_data["individual_start_time"] or self.shift.start_time
            end = cleaned_data["individual_end_time"] or self.shift.end_time
            if end < start:
                self.add_error("individual_end_time", _("End time must not be before start time."))
            return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        result = super().save()
        if comment := self.cleaned_data["comment"]:
            ParticipationComment.objects.create(
                participation=result,
                text=comment,
                authored_by_responsible=self.acting_user,
                visible_for=self.get_comment_visibility(),
            )
        return result

    class Meta:
        model = AbstractParticipation
        fields = ["individual_start_time", "individual_end_time"]

    def __init__(self, *args, **kwargs):
        instance = kwargs["instance"]
        self.acting_user = kwargs.pop("acting_user", None)
        kwargs["initial"] = {
            **kwargs.get("initial", {}),
            "individual_start_time": instance.individual_start_time or self.shift.start_time,
            "individual_end_time": instance.individual_end_time or self.shift.end_time,
        }
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.comments.exists():
            self.fields["previous_comments"] = forms.CharField(
                widget=PreviousCommentWidget(
                    comments=(
                        self.instance.comments.all()
                        if self.acting_user
                        and self.acting_user.has_perm(
                            "core.change_event", obj=self.instance.shift.event
                        )
                        else self.instance.comments.filter(
                            visible_for__in=[
                                ParticipationComment.Visibility.PUBLIC,
                                ParticipationComment.Visibility.PARTICIPANT,
                            ]
                        )
                    )
                ),
                required=False,
            )

    def get_customization_notification_info(self):
        """
        Return a list of human-readable messages for changed participation attributes responsibles should be informed about.
        This should not include the participation state, but customization aspects such as individual times, detailed disposition information, etc.
        """
        assert self.is_valid()
        info = []
        for time in ["start_time", "end_time"]:
            if (field_name := f"individual_{time}") in self.changed_data:
                text = _("{label} was changed from {initial} to {current}.").format(
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
                info.append(text)

        return info


class SignupForm(BaseParticipationForm):
    class SignupChoices(models.TextChoices):
        SIGNUP = "sign_up", _("Sign up")
        CUSTOMIZE = "customize", _("Customize")
        DECLINE = "decline", _("Decline")

    signup_choice = forms.ChoiceField(
        label=_("Signup choice"),
        choices=SignupChoices.choices,
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
                    f'<button class="btn btn-secondary mt-1 ms-1 float-end" type="submit" name="signup_choice" value="decline" formnovalidate>{_("Decline")}</button>'
                )
            )
        return buttons

    def __init__(self, *args, **kwargs):
        self.shift: Shift = kwargs.pop("shift")
        self.participant: AbstractParticipant = kwargs.pop("participant")
        super().__init__(*args, **kwargs)
        self._collect_fields()
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

    def _collect_fields(self):
        for fieldname, field in collect_signup_form_fields(
            self.shift, self.participant, self.instance, self.data.get("signup_choice")
        ):
            self.fields[fieldname] = field["form_class"](**field.get("form_kwargs", {}))

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
        self.request = kwargs.pop("request")
        self.description = kwargs.pop("description", "")
        super().__init__(*args, **kwargs)

    def get_context(self):
        return super().get_context() | {
            "request": self.request,
            "event": self.event,
            "shift": self.shift,
        }
