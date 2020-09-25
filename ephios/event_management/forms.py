from datetime import datetime, timedelta

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms import DateField, ModelForm, ModelMultipleChoiceField, Select, TimeField
from django.utils.timezone import make_aware
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget
from guardian.shortcuts import assign_perm, remove_perm

from ephios.event_management import signup
from ephios.event_management.models import Event, Shift
from ephios.extra.widgets import CustomDateInput, CustomTimeInput
from ephios.user_management.models import UserProfile
from ephios.user_management.widgets import MultiUserProfileWidget


class EventForm(ModelForm):
    visible_for = ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        label=_("Visible for"),
        help_text=_("Select groups which the event shall be visible for."),
        widget=Select2MultipleWidget,
        required=False,
    )
    responsible_persons = ModelMultipleChoiceField(
        queryset=UserProfile.objects.all(),
        required=False,
        label=_("Responsible persons"),
        widget=MultiUserProfileWidget,
    )
    responsible_groups = ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label=_("Responsible groups"),
        widget=Select2MultipleWidget,
    )

    class Meta:
        model = Event
        fields = ["title", "description", "location", "type", "mail_updates"]

    def save(self, commit=True):
        create = not self.instance.pk
        event = super().save(commit)
        if "visible_for" in self.changed_data or create:
            for group in self.cleaned_data["visible_for"]:
                assign_perm("view_event", group, event)
            for group in self.fields["visible_for"].queryset.exclude(
                id__in=self.cleaned_data["visible_for"]
            ):
                remove_perm("view_event", group, event)
        if "responsible_groups" in self.changed_data or create:
            for group in self.cleaned_data["responsible_groups"].exclude(
                id__in=self.initial["responsible_groups"]
            ):
                assign_perm("change_event", group, event)
                assign_perm("view_event", group, event)
            for group in self.initial["responsible_groups"].exclude(
                id__in=self.cleaned_data["responsible_groups"]
            ):
                remove_perm("change_event", group, event)
                if group not in self.cleaned_data["visible_for"]:
                    remove_perm("view_event", group, event)
        if "responsible_persons" in self.changed_data or create:
            for user in self.cleaned_data["responsible_persons"].exclude(
                id__in=self.initial["responsible_persons"]
            ):
                assign_perm("change_event", user, event)
                assign_perm("view_event", user, event)
            for user in self.initial["responsible_persons"].exclude(
                id__in=self.cleaned_data["responsible_persons"]
            ):
                remove_perm("change_event", user, event)
                remove_perm("view_event", user, event)
        return event


class ShiftForm(ModelForm):
    date = DateField(widget=CustomDateInput(format="%Y-%m-%d"))
    meeting_time = TimeField(widget=CustomTimeInput)
    start_time = TimeField(widget=CustomTimeInput)
    end_time = TimeField(widget=CustomTimeInput)

    field_order = ["date", "meeting_time", "start_time", "end_time", "signup_method_slug"]

    class Meta:
        model = Shift
        fields = ["meeting_time", "start_time", "end_time", "signup_method_slug"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["signup_method_slug"].widget = Select(
            choices=((method.slug, method.verbose_name) for method in signup.all_signup_methods())
        )

    def clean(self):
        cleaned_data = super().clean()
        if {"date", "meeting_time", "start_time", "end_time"} <= set(cleaned_data.keys()):
            cleaned_data["meeting_time"] = make_aware(
                datetime.combine(cleaned_data["date"], cleaned_data["meeting_time"])
            )
            cleaned_data["start_time"] = make_aware(
                datetime.combine(cleaned_data["date"], cleaned_data["start_time"])
            )
            cleaned_data["end_time"] = make_aware(
                datetime.combine(self.cleaned_data["date"], cleaned_data["end_time"])
            )
            if self.cleaned_data["end_time"] <= self.cleaned_data["start_time"]:
                cleaned_data["end_time"] = cleaned_data["end_time"] + timedelta(days=1)
            if not cleaned_data["meeting_time"] <= cleaned_data["start_time"]:
                raise ValidationError(_("Meeting time must not be after start time!"))
        return cleaned_data
