from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import DateField, Form, ModelForm, ModelMultipleChoiceField, Select, TimeField
from django.utils.timezone import make_aware
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.forms import PreferenceForm
from guardian.shortcuts import assign_perm, get_objects_for_user, get_users_with_perms, remove_perm
from recurrence.forms import RecurrenceField

from ephios.core import signup
from ephios.core.models import Event, EventType, LocalParticipation, Shift, UserProfile
from ephios.core.registries import event_type_preference_registry
from ephios.core.widgets import MultiUserProfileWidget
from ephios.extra.permissions import get_groups_with_perms
from ephios.extra.widgets import CustomDateInput, CustomTimeInput


class EventForm(ModelForm):
    visible_for = ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        label=_("Visible for"),
        help_text=_(
            "Select groups which the event shall be visible for. Regardless, the event will be visible for users that already signed up."
        ),
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
        fields = ["title", "description", "location", "mail_updates"]

    def __init__(self, **kwargs):
        user = kwargs.pop("user")
        can_publish_for_groups = get_objects_for_user(user, "publish_event_for_group", klass=Group)

        if (event := kwargs.get("instance", None)) is not None:
            self.eventtype = event.type
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
            self.eventtype = kwargs.pop("eventtype")
            kwargs["initial"] = {
                "responsible_users": self.eventtype.preferences.get("responsible_users")
                or get_user_model().objects.filter(pk=user.pk),
                "responsible_groups": self.eventtype.preferences.get("responsible_groups"),
                "visible_for": self.eventtype.preferences.get("visible_for")
                or get_objects_for_user(user, "publish_event_for_group", klass=Group),
            }
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
        event = super().save(commit=False)
        event.type = self.eventtype
        if commit:
            event.save()

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

        # assign view permissions to users that already have some sort of participation for the event
        # (-> they saw and interacted with it)
        participating_users = UserProfile.objects.filter(
            pk__in=LocalParticipation.objects.filter(shift_id__in=event.shifts.all()).values_list(
                "user", flat=True
            )
        )
        assign_perm("view_event", participating_users, event)

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


class EventDuplicationForm(Form):
    start_date = DateField(
        widget=CustomDateInput(format="%Y-%m-%d"),
        initial=date.today(),
        help_text=_(
            "This date will be used as the start date for recurring events that you create below, e.g. daily events will be created from this date onwards."
        ),
    )
    recurrence = RecurrenceField(required=False)


class EventTypeForm(ModelForm):
    class Meta:
        model = EventType
        fields = ["title", "can_grant_qualification"]


class EventTypePreferenceForm(PreferenceForm):
    registry = event_type_preference_registry
