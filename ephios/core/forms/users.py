from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Fieldset, Layout, Submit
from django import forms
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import (
    CheckboxSelectMultiple,
    Form,
    ModelForm,
    ModelMultipleChoiceField,
    MultipleChoiceField,
    PasswordInput,
    inlineformset_factory,
)
from django.urls import reverse
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget, Select2Widget
from guardian.shortcuts import assign_perm, get_objects_for_group, remove_perm

from ephios.core.consequences import WorkingHoursConsequenceHandler
from ephios.core.models import QualificationGrant, UserProfile, WorkingHours
from ephios.core.models.users import IdentityProvider
from ephios.core.services.notifications.backends import enabled_notification_backends
from ephios.core.services.notifications.types import enabled_notification_types
from ephios.core.signals import register_group_permission_fields
from ephios.core.widgets import MultiUserProfileWidget
from ephios.extra.crispy import AbortLink
from ephios.extra.permissions import PermissionField, PermissionFormMixin, get_groups_with_perms
from ephios.extra.widgets import CustomDateInput
from ephios.modellogging.log import add_log_recorder
from ephios.modellogging.recorders import DerivedFieldsLogRecorder

PLANNING_TEST_PERMISSION = "core.add_event"

PLANNING_PERMISSIONS = [
    "core.add_event",
    "core.delete_event",
]

HR_TEST_PERMISSION = "core.change_userprofile"

HR_PERMISSIONS = [
    "core.add_userprofile",
    "core.change_userprofile",
    "core.delete_userprofile",
    "core.view_userprofile",
]

MANAGEMENT_TEST_PERMISSION = "auth.change_group"

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
    "auth.publish_event_for_group",
    "modellogging.view_logentry",
]


def get_group_permission_log_fields(group):
    # This lives here because it is closely related to the fields on GroupForm below
    if not group.pk:
        return {}
    perms = set(
        f"{g[0]}.{g[1]}"
        for g in group.permissions.values_list("content_type__app_label", "codename")
    )

    return {
        _("Can add events"): PLANNING_TEST_PERMISSION in perms,
        _("Can edit users"): HR_TEST_PERMISSION in perms,
        _("Can change permissions"): MANAGEMENT_TEST_PERMISSION in perms,
        # force evaluation of querysets
        _("Can publish events for groups"): set(
            get_objects_for_group(group, "publish_event_for_group", klass=Group)
        ),
        _("Can decide working hours for groups"): set(
            get_objects_for_group(group, "decide_workinghours_for_group", klass=Group)
        ),
    }


class GroupForm(PermissionFormMixin, ModelForm):
    is_planning_group = PermissionField(
        label=_("Can add events"),
        permissions=PLANNING_PERMISSIONS,
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
            "If checked, users in this group can view, add, edit and delete users. "
            "They can also manage group memberships for their own groups."
        ),
        permissions=HR_PERMISSIONS,
        required=False,
    )
    is_management_group = PermissionField(
        label=_("Can change permissions and manage ephios"),
        help_text=_(
            "If checked, users in this group can edit all users, change groups, their permissions and memberships "
            "as well as define eventtypes and qualifications."
        ),
        permissions=MANAGEMENT_PERMISSIONS,
        required=False,
    )

    users = ModelMultipleChoiceField(
        label=_("Users"),
        queryset=UserProfile.objects.all(),
        widget=MultiUserProfileWidget,
        required=False,
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
        extra_fields = [
            item for __, result in register_group_permission_fields.send(None) for item in result
        ]
        for field_name, field in extra_fields:
            self.base_fields[field_name] = field
        super().__init__(**kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("name"),
            Field("users"),
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
            Fieldset(
                _("Other"),
                *(Field(entry[0]) for entry in extra_fields),
            ),
            FormActions(
                Submit("submit", _("Save"), css_class="float-end"),
                AbortLink(href=reverse("core:group_list")),
            ),
        )

    def clean_is_management_group(self):
        is_management_group = self.cleaned_data["is_management_group"]
        if self.fields["is_management_group"].initial and not is_management_group:
            other_management_groups = get_groups_with_perms(
                only_with_perms_in=MANAGEMENT_PERMISSIONS,
                must_have_all_perms=True,
            ).exclude(pk=self.instance.pk)
            if not other_management_groups.exists():
                raise ValidationError(
                    _(
                        "At least one group with management permissions must exist. "
                        "Please promote another group before demoting this one."
                    )
                )
        if is_management_group:
            self.cleaned_data["is_hr_group"] = True
        return is_management_group

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


class UserProfileForm(PermissionFormMixin, ModelForm):
    groups = ModelMultipleChoiceField(
        label=_("Groups"),
        queryset=Group.objects.all(),
        widget=Select2MultipleWidget,
        required=False,
        disabled=True,  # explicitly enable for users with `change_group` permission
    )
    is_staff = PermissionField(
        label=_("Administrator"),
        help_text=_(
            "If checked, this user can change technical ephios settings as well as edit all user profiles, "
            "groups, qualifications, events and event types."
        ),
        permissions=MANAGEMENT_PERMISSIONS,
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
        if not request.user.is_staff:
            self.fields["is_staff"].disabled = True
            self.fields["is_staff"].help_text += " " + _(
                "Only other technical administrators can change this."
            )

        # email change can be used for account takeover, so only allow that in specific cases
        if self.instance.pk is not None and not (
            request.user.is_staff  # staff user can change email
            or self.instance == request.user  # user can change own email
            or not self.instance.is_staff
            and (  # if modifying a non-staff user
                # users that can modify groups can change email
                request.user.has_perm("auth.change_group")
                # or the modified user is not in a group that the modifying user is not in
                or set(request.user.groups.all()) >= set(self.instance.groups.all())
            )
        ):
            self.fields["email"].disabled = True
            self.fields["email"].help_text = _(
                "You are not allowed to change the email address of this user."
            )

    @property
    def permission_target(self):
        return self.instance

    field_order = [
        "email",
        "display_name",
        "date_of_birth",
        "phone",
        "groups",
        "is_active",
        "is_staff",
    ]

    class Meta:
        model = UserProfile
        fields = [
            "email",
            "display_name",
            "date_of_birth",
            "phone",
            "is_active",
            "is_staff",
        ]
        widgets = {"date_of_birth": CustomDateInput}
        help_texts = {
            "is_active": _("Inactive users cannot log in and do not get any notifications.")
        }
        labels = {"is_active": _("Active user")}

    def clean_is_staff(self):
        if self.initial.get("is_staff", False) and not self.cleaned_data["is_staff"]:
            other_staff = UserProfile.objects.filter(is_staff=True).exclude(pk=self.instance.pk)
            if not other_staff.exists():
                raise ValidationError(
                    _(
                        "At least one user must be technical administrator. Please promote another user before demoting this one."
                    )
                )
        return self.cleaned_data["is_staff"]

    def save(self, commit=True):
        userprofile = super().save(commit)
        userprofile.groups.set(
            Group.objects.filter(
                Q(id__in=self.cleaned_data["groups"]) | Q(id__in=(g.id for g in self.locked_groups))
            )
        )
        # if the user is re-activated after the email has been deemed invalid, reset the flag
        if userprofile.is_active and userprofile.email_invalid:
            userprofile.email_invalid = False
        userprofile.save()
        return userprofile


class DeleteUserProfileForm(Form):
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance")
        super().__init__(*args, **kwargs)

    def clean(self):
        other_staff = UserProfile.objects.filter(is_staff=True).exclude(pk=self.instance.pk)
        if self.instance.is_staff and not other_staff.exists():
            raise ValidationError(
                _(
                    "At least one user must be technical administrator. "
                    "Please promote another user before deleting this one."
                )
            )


class DeleteGroupForm(Form):
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance")
        super().__init__(*args, **kwargs)

    def clean(self):
        management_groups = get_groups_with_perms(
            only_with_perms_in=MANAGEMENT_PERMISSIONS, must_have_all_perms=True
        )

        if (
            self.instance in management_groups
            and not management_groups.exclude(pk=self.instance.pk).exists()
        ):
            raise ValidationError(
                _(
                    "At least one group with management permissions must exist. "
                    "Please promote another group before deleting this one."
                )
            )


class QualificationGrantForm(ModelForm):
    model = QualificationGrant

    class Meta:
        fields = ["qualification", "expires"]
        widgets = {"qualification": Select2Widget}

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


class WorkingHourRequestForm(ModelForm):
    date = forms.DateField(widget=CustomDateInput)

    class Meta:
        model = WorkingHours
        fields = ["date", "hours", "reason"]

    def __init__(self, *args, **kwargs):
        self.can_grant = kwargs.pop("can_grant", False)
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Field("date"),
            Field("hours"),
            Field("reason"),
            FormActions(
                Submit("submit", _("Save"), css_class="float-end"),
            ),
        )

    def create_consequence(self):
        WorkingHoursConsequenceHandler.create(
            user=self.user,
            when=self.cleaned_data["date"],
            hours=float(self.cleaned_data["hours"]),
            reason=self.cleaned_data["reason"],
        )


class UserNotificationPreferenceForm(Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        self.all_backends = {backend.slug for backend in enabled_notification_backends()}
        for notification_type in enabled_notification_types():
            if notification_type.unsubscribe_allowed:
                self.fields[notification_type.slug] = MultipleChoiceField(
                    label=notification_type.title,
                    choices=[
                        (backend.slug, backend.title) for backend in enabled_notification_backends()
                    ],
                    initial=list(
                        self.all_backends
                        - {
                            backend
                            for backend, notificaton_type in self.user.disabled_notifications
                            if notificaton_type == notification_type.slug
                        }
                    ),
                    widget=CheckboxSelectMultiple,
                    required=False,
                )

    def save_preferences(self):
        disabled_notifications = []
        for notification_type, preferred_backends in self.cleaned_data.items():
            for backend in self.all_backends - set(preferred_backends):
                disabled_notifications.append([backend, notification_type])
        self.user.disabled_notifications = disabled_notifications
        self.user.save()


class UserOwnDataForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = ["preferred_language"]


class OIDCDiscoveryForm(Form):
    url = forms.URLField(
        label=_("OIDC Provider URL"), help_text=_("The base URL of the OIDC provider.")
    )

    def clean_url(self):
        url = self.cleaned_data["url"]
        if not url.endswith("/"):
            url += "/"
        return url


class IdentityProviderForm(ModelForm):
    class Meta:
        model = IdentityProvider
        fields = [
            "label",
            "client_id",
            "client_secret",
            "scopes",
            "default_groups",
            "group_claim",
            "create_missing_groups",
            "authorization_endpoint",
            "token_endpoint",
            "userinfo_endpoint",
            "end_session_endpoint",
            "jwks_uri",
        ]
        widgets = {
            "default_groups": Select2MultipleWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["client_secret"] = forms.CharField(
                widget=PasswordInput(attrs={"placeholder": "********"}),
                required=False,
                label=_("Client secret"),
                help_text=_("Leave empty to keep the current secret."),
            )

    def clean_client_secret(self):
        client_secret = self.cleaned_data["client_secret"]
        if self.instance.pk and client_secret == "":
            return self.instance.client_secret
        return client_secret
