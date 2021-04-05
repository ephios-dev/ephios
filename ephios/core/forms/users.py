from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Fieldset, Layout, Submit
from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms import (
    CharField,
    CheckboxSelectMultiple,
    DateField,
    DecimalField,
    Form,
    ModelForm,
    ModelMultipleChoiceField,
    MultipleChoiceField,
    inlineformset_factory,
)
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget, Select2Widget
from guardian.shortcuts import assign_perm, get_objects_for_group, remove_perm

from ephios.core.consequences import WorkingHoursConsequenceHandler
from ephios.core.models import QualificationGrant, UserProfile
from ephios.core.services.notifications.backends import enabled_notification_backends
from ephios.core.services.notifications.types import enabled_notification_types
from ephios.core.widgets import MultiUserProfileWidget
from ephios.extra.permissions import PermissionField, PermissionFormMixin
from ephios.extra.widgets import CustomDateInput
from ephios.modellogging.log import add_log_recorder
from ephios.modellogging.recorders import DerivedFieldsLogRecorder

MANAGEMENT_PERMISSIONS = [
    "auth.add_group",
    "auth.change_group",
    "auth.delete_group",
    "auth.view_group",
    "core.add_userprofile",
    "core.change_userprofile",
    "core.delete_userprofile",
    "core.view_userprofile",
    "core.view_event",
    "core.add_event",
    "core.change_event",
    "core.delete_event",
    "core.view_eventtype",
    "core.add_eventtype",
    "core.change_eventtype",
    "core.delete_eventtype",
    "core.view_qualification",
    "core.add_qualification",
    "core.change_qualification",
    "core.delete_qualification",
    "modellogging.view_logentry",
]


def get_group_permission_log_fields(group):
    # This lives here because it is closely related to the fields on GroupForm below
    if not group.pk:
        return {}
    perms = set(group.permissions.values_list("codename", flat=True))

    return {
        _("Can view past events"): "view_past_event" in perms,
        _("Can add events"): "add_event" in perms,
        _("Can edit users"): "change_userprofile" in perms,
        _("Can manage ephios"): "change_group" in perms,
        # force evaluation of querysets
        _("Can publish events for groups"): set(
            get_objects_for_group(group, "publish_event_for_group", klass=Group)
        ),
        _("Can decide working hours for groups"): set(
            get_objects_for_group(group, "decide_workinghours_for_group", klass=Group)
        ),
    }


class GroupForm(PermissionFormMixin, ModelForm):
    can_view_past_event = PermissionField(
        label=_("Can view past events"), permissions=["core.view_past_event"], required=False
    )

    is_planning_group = PermissionField(
        label=_("Can add events"),
        permissions=["core.add_event", "core.delete_event"],
        required=False,
    )
    publish_event_for_group = ModelMultipleChoiceField(
        label=_("Can publish events for groups"),
        queryset=Group.objects.all(),
        required=False,
        help_text=_("Choose groups that this group can make events visible for."),
        widget=Select2MultipleWidget,
    )
    decide_workinghours_for_group = ModelMultipleChoiceField(
        label=_("Can decide working hours for groups"),
        queryset=Group.objects.all(),
        required=False,
        help_text=_(
            "Choose groups that the group you are currently editing can decide whether to grant working hours for."
        ),
        widget=Select2MultipleWidget,
    )

    is_hr_group = PermissionField(
        label=_("Can edit users"),
        help_text=_(
            "If checked, users in this group can view, add, edit and delete users. They can also manage group memberships for their own groups."
        ),
        permissions=[
            "core.add_userprofile",
            "core.change_userprofile",
            "core.delete_userprofile",
            "core.view_userprofile",
        ],
        required=False,
    )
    is_management_group = PermissionField(
        label=_("Can manage ephios"),
        help_text=_(
            "If checked, users in this group can manage users, groups, all group memberships, eventtypes and qualifications"
        ),
        permissions=MANAGEMENT_PERMISSIONS,
        required=False,
    )

    users = ModelMultipleChoiceField(
        label=_("Users"), queryset=UserProfile.objects.all(), widget=MultiUserProfileWidget
    )

    class Meta:
        model = Group
        fields = ["name"]

    def __init__(self, **kwargs):
        if (group := kwargs.get("instance", None)) is not None:
            kwargs["initial"] = {
                "users": group.user_set.all(),
                "publish_event_for_group": get_objects_for_group(
                    group, "publish_event_for_group", klass=Group
                ),
                "decide_workinghours_for_group": get_objects_for_group(
                    group, "decide_workinghours_for_group", klass=Group
                ),
                **kwargs.get("initial", {}),
            }
            self.permission_target = group
        super().__init__(**kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("name"),
            Field("users"),
            Field("can_view_past_event"),
            Fieldset(
                _("Management"),
                Field("is_hr_group", title="This permission is included with the management role."),
                "is_management_group",
            ),
            Fieldset(
                _("Planning"),
                Field(
                    "is_planning_group",
                    title="This permission is included with the management role.",
                ),
                Field("publish_event_for_group", wrapper_class="publish-select"),
                "decide_workinghours_for_group",
            ),
            FormActions(Submit("submit", _("Save"))),
        )

    def save(self, commit=True):
        add_log_recorder(self.instance, DerivedFieldsLogRecorder(get_group_permission_log_fields))
        group = super().save(commit)

        group.user_set.set(self.cleaned_data["users"])

        remove_perm("publish_event_for_group", group, Group.objects.all())
        if group.permissions.filter(codename="add_event").exists():
            assign_perm(
                "publish_event_for_group", group, self.cleaned_data["publish_event_for_group"]
            )

        if "decide_workinghours_for_group" in self.changed_data:
            remove_perm("decide_workinghours_for_group", group, Group.objects.all())
            assign_perm(
                "decide_workinghours_for_group",
                group,
                self.cleaned_data["decide_workinghours_for_group"],
            )

        group.save()  # logging
        return group


class UserProfileForm(ModelForm):
    groups = ModelMultipleChoiceField(
        label=_("Groups"),
        queryset=Group.objects.all(),
        widget=Select2MultipleWidget,
        required=False,
        disabled=True,  # explicitly enable for users with `change_group` permission
    )

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.locked_groups = set()
        if request.user.has_perm("auth.change_group"):
            self.fields["groups"].disabled = False
        elif allowed_groups := request.user.groups:
            self.fields["groups"].disabled = False
            self.fields["groups"].queryset = allowed_groups
            if self.instance.pk:
                self.locked_groups = set(self.instance.groups.exclude(id__in=allowed_groups.all()))
            if self.locked_groups:
                self.fields["groups"].help_text = _(
                    "The user is also member of <b>{groups}</b>, but you are not allowed to manage memberships for those groups."
                ).format(groups=", ".join((group.name for group in self.locked_groups)))

    field_order = [
        "email",
        "first_name",
        "last_name",
        "date_of_birth",
        "phone",
        "groups",
        "is_active",
    ]

    class Meta:
        model = UserProfile
        fields = ["email", "first_name", "last_name", "date_of_birth", "phone", "is_active"]
        widgets = {"date_of_birth": CustomDateInput(format="%Y-%m-%d")}
        help_texts = {
            "is_active": _("Inactive users cannot log in and do not get any notifications.")
        }
        labels = {"is_active": _("Active user")}

    def save(self, commit=True):
        userprofile = super().save(commit)
        userprofile.groups.set(
            Group.objects.filter(
                Q(id__in=self.cleaned_data["groups"]) | Q(id__in=(g.id for g in self.locked_groups))
            )
        )
        userprofile.save()
        return userprofile


class QualificationGrantForm(ModelForm):
    model = QualificationGrant

    class Meta:
        fields = ["qualification", "expires"]
        widgets = {"qualification": Select2Widget, "expires": CustomDateInput(format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, "instance") and self.instance.pk:
            # Hide the field and simply display the qualification name in the template
            self.fields["qualification"].disabled = True
            self.fields["qualification"].widget = forms.HiddenInput()
            self.fields["qualification"].title = self.instance.qualification.title


QualificationGrantFormset = inlineformset_factory(
    UserProfile,
    QualificationGrant,
    form=QualificationGrantForm,
    extra=0,
)


class QualificationGrantFormsetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_class = "col-md-4"
        self.field_class = "col-md-8"


class WorkingHourRequestForm(Form):
    when = DateField(widget=CustomDateInput, label=_("Date"))
    hours = DecimalField(label=_("Hours of work"), min_value=0.5)
    reason = CharField(label=_("Occasion"))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.add_input(Submit("submit", _("Submit")))

    def create_consequence(self):
        WorkingHoursConsequenceHandler.create(
            user=self.request.user,
            when=self.cleaned_data["when"],
            hours=float(self.cleaned_data["hours"]),
            reason=self.cleaned_data["reason"],
        )


class UserNotificationPreferenceForm(Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        preferences = self.user.preferences["notifications__notifications"]
        for notification_type in enabled_notification_types():
            if notification_type.unsubscribe_allowed:
                self.fields[notification_type.slug] = MultipleChoiceField(
                    label=notification_type.title,
                    choices=[
                        (backend.slug, backend.title) for backend in enabled_notification_backends()
                    ],
                    initial=preferences.get(notification_type.slug, {}),
                    widget=CheckboxSelectMultiple,
                    required=False,
                )

    def update_preferences(self):
        self.user.preferences["notifications__notifications"] = self.cleaned_data
