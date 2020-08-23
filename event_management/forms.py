from datetime import datetime, timedelta

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms import (
    ModelForm,
    ModelMultipleChoiceField,
    modelformset_factory,
    Select,
    DateField,
    TimeField,
)
from guardian.shortcuts import assign_perm

from event_management.models import Event, Shift
from event_management.signup import register_signup_methods
from jep.widgets import CustomDateInput, CustomTimeInput
from user_management.models import UserProfile


class EventForm(ModelForm):
    visible_for = ModelMultipleChoiceField(queryset=Group.objects.none())
    responsible_persons = ModelMultipleChoiceField(
        queryset=UserProfile.objects.all(), required=False
    )
    responsible_groups = ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)

    class Meta:
        model = Event
        fields = ["title", "description", "location", "type"]

    def save(self, commit=True):
        event = super(EventForm, self).save(commit)
        for group in self.cleaned_data["visible_for"]:
            assign_perm("view_event", group, event)
        for group in self.cleaned_data["responsible_groups"]:
            assign_perm("change_event", group, event)
        for user in self.cleaned_data["responsible_persons"]:
            assign_perm("change_event", user, event)
        return event


class ShiftForm(ModelForm):
    date = DateField(widget=CustomDateInput)
    meeting_time = TimeField(widget=CustomTimeInput)
    start_time = TimeField(widget=CustomTimeInput)
    end_time = TimeField(widget=CustomTimeInput)

    class Meta:
        model = Shift
        fields = ["signup_method_slug"]
        widgets = {
            "signup_method_slug": Select(
                choices=(
                    (method.slug, method.verbose_name)
                    for receiver, method in register_signup_methods.send(None)
                )
            )
        }

    def clean(self):
        cleaned_data = super(ShiftForm, self).clean()
        if not cleaned_data["meeting_time"] <= cleaned_data["start_time"]:
            raise ValidationError("Meeting time must not be after start time!")
        return cleaned_data

    def save(self, commit=True):
        shift = super().save(commit)
        shift.meeting_time = datetime.combine(
            self.cleaned_data["date"], self.cleaned_data["meeting_time"]
        )
        shift.start_time = datetime.combine(
            self.cleaned_data["date"], self.cleaned_data["start_time"]
        )
        if self.cleaned_data["end_time"] <= self.cleaned_data["start_time"]:
            end_date = self.cleaned_data["date"] + timedelta(days=1)
        else:
            end_date = self.cleaned_data["date"]
        shift.end_time = datetime.combine(end_date, self.cleaned_data["end_time"])
        return shift.save() if commit else shift


ShiftFormSet = modelformset_factory(Shift, form=ShiftForm,)
