import operator
import re
from datetime import date, datetime, timedelta

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms.utils import from_current_timezone
from django.utils.timezone import make_aware
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.forms import PreferenceForm
from guardian.shortcuts import assign_perm, get_objects_for_user, get_users_with_perms, remove_perm
from recurrence.forms import RecurrenceField

from ephios.core.dynamic_preferences_registry import event_type_preference_registry
from ephios.core.models import Event, EventType, LocalParticipation, Shift, UserProfile
from ephios.core.signup.flow import enabled_signup_flows, signup_flow_from_slug
from ephios.core.signup.structure import enabled_shift_structures, shift_structure_from_slug
from ephios.core.widgets import MultiUserProfileWidget
from ephios.extra.colors import clear_eventtype_color_css_fragment_cache
from ephios.extra.crispy import AbortLink
from ephios.extra.permissions import get_groups_with_perms
from ephios.extra.widgets import ColorInput, CustomDateInput, CustomTimeInput
from ephios.modellogging.log import add_log_recorder, update_log
from ephios.modellogging.recorders import (
    DerivedFieldsLogRecorder,
    InstanceActionType,
    PermissionLogRecorder,
)


class EventForm(forms.ModelForm):
    visible_for = forms.ModelMultipleChoiceField(
        queryset=Group.objects.none(),
        label=_("Visible for"),
        help_text=_(
            "Select groups which the event shall be visible for. Regardless, the event will be visible for users that already signed up."
        ),
        widget=Select2MultipleWidget,
        required=False,
    )
    responsible_users = forms.ModelMultipleChoiceField(
        queryset=UserProfile.objects.all(),
        required=False,
        label=_("Responsible persons"),
        widget=MultiUserProfileWidget,
    )
    responsible_groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label=_("Responsible groups"),
        widget=Select2MultipleWidget,
    )

    class Meta:
        model = Event
        fields = ["title", "type", "description", "location"]

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

        if event is None:
            self.fields.pop("type")
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
        if not self.instance.pk:
            self.instance.type = self.eventtype
        event: Event = super().save(commit=commit)

        add_log_recorder(event, PermissionLogRecorder("view_event", _("Visible for")))
        add_log_recorder(event, PermissionLogRecorder("change_event", _("Responsibles")))

        # delete existing permissions
        # (better implement https://github.com/django-guardian/django-guardian/issues/654)
        for group in get_groups_with_perms(
            event, only_with_perms_in=["view_event", "change_event"], must_have_all_perms=False
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
        assign_perm("change_event", self.cleaned_data["responsible_users"], event)

        # Assign view_event to responsible users  and to non-responsible users
        # that already have some sort of participation for the event
        # (-> they saw and interacted with it)
        # We can't just do users that aren't included by group permissions,
        # as they might get removed from that group.
        assign_perm(
            "view_event",
            UserProfile.objects.filter(
                Q(pk__in=self.cleaned_data["responsible_users"])
                | Q(
                    pk__in=LocalParticipation.objects.filter(
                        shift_id__in=event.shifts.all()
                    ).values_list("user", flat=True)
                )
            ),
            event,
        )

        update_log(event, InstanceActionType.CHANGE)
        return event


class ShiftForm(forms.ModelForm):
    date = forms.DateField(widget=CustomDateInput, label=_("Date"))
    meeting_time = forms.TimeField(widget=CustomTimeInput, label=_("Meeting time"))
    start_time = forms.TimeField(widget=CustomTimeInput, label=_("Start time"))
    end_time = forms.TimeField(widget=CustomTimeInput, label=_("End time"))

    field_order = [
        "date",
        "meeting_time",
        "start_time",
        "end_time",
        "signup_flow_slug",
        "structure_slug",
    ]

    class Meta:
        model = Shift
        fields = ["meeting_time", "start_time", "end_time", "signup_flow_slug", "structure_slug"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        signup_flows = list(enabled_signup_flows())
        # make sure that if a shift uses a disabled but installed flow, it is also available in the list
        if self.instance and (flow_slug := self.instance.signup_flow_slug):
            if flow_slug not in map(operator.attrgetter("slug"), signup_flows):
                try:
                    signup_flows.append(signup_flow_from_slug(flow_slug, self.instance))
                except ValueError:  # not installed
                    pass
        self.fields["signup_flow_slug"].widget = forms.Select(
            choices=((flow.slug, flow.verbose_name) for flow in signup_flows)
        )
        # same for structure
        shift_structures = list(enabled_shift_structures())
        if self.instance and (structure_slug := self.instance.structure_slug):
            if structure_slug not in map(operator.attrgetter("slug"), shift_structures):
                try:
                    shift_structures.append(
                        shift_structure_from_slug(structure_slug, self.instance)
                    )
                except ValueError:  # not installed
                    pass
        self.fields["structure_slug"].widget = forms.Select(
            choices=((structure.slug, structure.verbose_name) for structure in shift_structures)
        )
        # this recorder may cause db queries, so it's not added on Shift init, but here in the form
        # pylint: disable=undefined-variable
        add_log_recorder(
            self.instance,
            DerivedFieldsLogRecorder(lambda shift: shift.get_signup_info()),
        )

    def clean_meeting_time(self):
        return from_current_timezone(
            datetime.combine(self.cleaned_data["date"], self.cleaned_data["meeting_time"])
        )

    def clean_start_time(self):
        return from_current_timezone(
            datetime.combine(self.cleaned_data["date"], self.cleaned_data["start_time"])
        )

    def clean_end_time(self):
        end_time = datetime.combine(self.cleaned_data["date"], self.cleaned_data["end_time"])
        if make_aware(end_time) <= self.cleaned_data["start_time"]:
            end_time += timedelta(days=1)
        return from_current_timezone(end_time)

    def clean(self):
        cleaned_data = super().clean()
        if {"meeting_time", "start_time"} <= set(cleaned_data.keys()):
            if not cleaned_data["meeting_time"] <= cleaned_data["start_time"]:
                raise ValidationError(_("Meeting time must not be after start time!"))
        return cleaned_data


class EventDuplicationForm(forms.Form):
    start_date = forms.DateField(
        widget=CustomDateInput,
        initial=date.today(),
        help_text=_(
            "This date will be used as the start date for recurring events that you create below, e.g. daily events will be created from this date onwards."
        ),
        label=_("Start date"),
    )
    recurrence = RecurrenceField(required=False)


class EventTypeForm(forms.ModelForm):
    class Meta:
        model = EventType
        fields = ["title", "color"]
        widgets = {"color": ColorInput()}

    def clean_color(self):
        regex = re.compile(r"#[a-fA-F\d]{6}")
        if not regex.match(self.cleaned_data["color"]):
            raise ValidationError(_("You need to enter a valid color"))
        return self.cleaned_data["color"]

    def save(self, commit=True):
        clear_eventtype_color_css_fragment_cache()
        return super().save(commit=commit)


class EventTypePreferenceForm(PreferenceForm):
    registry = event_type_preference_registry


class BasePluginFormMixin:
    template_name = "core/fragments/plugin_form.html"

    @property
    def heading(self):
        raise NotImplementedError

    def is_function_active(self):
        """
        When building forms for additional features, return whether that feature is enabled for the form instance.
        With the default template, if this is True, the collapse is expanded on page load.
        """
        return False


class EventNotificationForm(forms.Form):
    NEW_EVENT = "new"
    REMINDER = "remind"
    PARTICIPANTS = "participants"
    action = forms.ChoiceField(
        choices=[
            (NEW_EVENT, _("Send notification about new event to everyone")),
            (REMINDER, _("Send reminder to everyone that is not participating")),
            (PARTICIPANTS, _("Send a message to all participants")),
        ],
        widget=forms.RadioSelect,
        label=False,
    )
    mail_content = forms.CharField(required=False, widget=forms.Textarea, label=_("Mail content"))

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop("event")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Field("action"),
            Field("mail_content"),
            FormActions(
                Submit("submit", _("Send"), css_class="float-end"),
                AbortLink(href=self.event.get_absolute_url()),
            ),
        )

    def clean(self):
        if (
            self.cleaned_data.get("action") == self.PARTICIPANTS
            and not self.cleaned_data["mail_content"]
        ):
            raise ValidationError(_("You cannot send an empty mail."))
        return super().clean()
