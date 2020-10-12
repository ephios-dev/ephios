from datetime import datetime, timedelta

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import DateField, ModelForm, ModelMultipleChoiceField, Select, TimeField
from django.utils.timezone import make_aware
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget
from guardian.shortcuts import (
    assign_perm,
    remove_perm,
    get_users_with_perms,
    get_objects_for_user,
)

from ephios.event_management import signup
from ephios.event_management.models import Event, Shift
from ephios.extra.permissions import get_groups_with_perms
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
    responsible_users = ModelMultipleChoiceField(
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

    def __init__(self, **kwargs):
        user = kwargs.pop("user")
        can_publish_for_groups = get_objects_for_user(user, "publish_event_for_group", klass=Group)

        if (event := kwargs.get("instance", None)) is not None:
            responsible_users = get_users_with_perms(
                event, only_with_perms_in=["change_event"], with_group_users=False
            )
            responsible_groups = get_groups_with_perms(event, only_with_perms_in=["change_event"])
            visible_for = get_groups_with_perms(event, only_with_perms_in=["view_event"]).exclude(
                id__in=responsible_groups
            )

            self.locked_visible_for_groups = set(visible_for.exclude(id__in=can_publish_for_groups))
            kwargs["initial"] = {
                "visible_for": visible_for.filter(id__in=can_publish_for_groups),
                "responsible_users": responsible_users,
                "responsible_groups": responsible_groups,
                **kwargs.get("initial", {}),
            }
        else:
            self.locked_visible_for_groups = set()

        super().__init__(**kwargs)

        self.fields["visible_for"].queryset = can_publish_for_groups
        self.fields["visible_for"].disabled = not can_publish_for_groups
        if self.locked_visible_for_groups:
            self.fields["visible_for"].help_text = _(
                "Select groups which the event shall be visible for. "
                "This event is also visible for <b>{groups}</b>, "
                "but you don't have the permission to change visibility "
                "for those groups."
            ).format(groups=", ".join(group.name for group in self.locked_visible_for_groups))

    def save(self, commit=True):
        event = super().save(commit)

        # delete existing permissions
        # (better implement https://github.com/django-guardian/django-guardian/issues/654)
        for group in get_groups_with_perms(
            event, only_with_perms_in=["view_event", "change_event"]
        ):
            remove_perm("view_event", group, event)
            remove_perm("change_event", group, event)
        for user in get_users_with_perms(event, only_with_perms_in=["view_event", "change_event"]):
            remove_perm("view_event", user, event)
            remove_perm("change_event", user, event)

        # assign designated permissions
        assign_perm(
            "view_event",
            Group.objects.filter(
                Q(id__in=self.cleaned_data["visible_for"])
                | Q(id__in=self.cleaned_data["responsible_groups"])
                | Q(id__in=(g.id for g in self.locked_visible_for_groups))
            ),
            event,
        )
        assign_perm("change_event", self.cleaned_data["responsible_groups"], event)
        assign_perm("view_event", self.cleaned_data["responsible_users"], event)
        assign_perm("change_event", self.cleaned_data["responsible_users"], event)

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
