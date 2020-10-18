from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.forms import BooleanField, ModelForm, ModelMultipleChoiceField, inlineformset_factory
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget, Select2Widget
from guardian.shortcuts import assign_perm, remove_perm, get_objects_for_group

from ephios.extra.widgets import CustomDateInput
from ephios.user_management.models import QualificationGrant, UserProfile
from ephios.user_management.widgets import MultiUserProfileWidget


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password_validation = forms.CharField(
        label=_("Password confirmation"), widget=forms.PasswordInput
    )
    field_order = ["email", "password", "password_validation"]

    class Meta:
        model = UserProfile
        fields = (
            "email",
            "first_name",
            "last_name",
            "date_of_birth",
            "phone",
        )

    def clean_password_validation(self):
        # Check that the two password entries match
        password = self.cleaned_data.get("password")
        password_validation = self.cleaned_data.get("password_validation")
        if password and password_validation and password != password_validation:
            raise forms.ValidationError(_("Passwords don't match"))
        return password_validation

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get("password_validation")
        if password:
            try:
                validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password", error)

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """

    password = ReadOnlyPasswordHashField()

    class Meta:
        model = UserProfile
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "date_of_birth",
            "phone",
            "is_active",
            "is_staff",
        )

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class GroupForm(ModelForm):
    publish_event_for_group = ModelMultipleChoiceField(
        label=_("Can publish events for groups"),
        queryset=Group.objects.all(),
        required=False,
        help_text=_("Choose groups that this group can make events visible for."),
        widget=Select2MultipleWidget,
    )
    can_view_past_event = BooleanField(label=_("Can view past events"), required=False)
    can_add_event = BooleanField(label=_("Can add events"), required=False)
    can_manage_user = BooleanField(
        label=_("Can manage users"),
        help_text=_("If checked, users in this group can view, add, edit and delete users."),
        required=False,
    )
    can_manage_group = BooleanField(
        label=_("Can manage groups"),
        help_text=_("If checked, users in this group can view, add, edit and delete groups."),
        required=False,
    )
    users = ModelMultipleChoiceField(
        label=_("Users"), queryset=UserProfile.objects.all(), widget=MultiUserProfileWidget
    )

    field_order = [
        "name",
        "users",
        "can_manage_user",
        "can_manage_group",
        "can_view_past_event",
        "can_add_event",
        "publish_event_for_group",
    ]

    class Meta:
        model = Group
        fields = ["name"]

    def __init__(self, **kwargs):
        if (group := kwargs.get("instance", None)) is not None:
            kwargs["initial"] = {
                "users": group.user_set.all(),
                "can_view_past_event": group.permissions.filter(
                    codename="view_past_event"
                ).exists(),
                "can_add_event": group.permissions.filter(codename="add_event").exists(),
                "publish_event_for_group": get_objects_for_group(
                    group, "publish_event_for_group", klass=Group
                ),
                "can_manage_user": group.permissions.filter(
                    codename__in=[
                        "add_userprofile",
                        "change_userprofile",
                        "delete_userprofile",
                        "view_userprofile",
                    ]
                ).exists(),
                "can_manage_group": group.permissions.filter(
                    codename__in=[
                        "add_group",
                        "change_group",
                        "delete_group",
                        "view_group",
                    ]
                ).exists(),
                **kwargs.get("initial", {}),
            }
        super().__init__(**kwargs)

    def save(self, commit=True):
        group = super().save(commit)

        group.user_set.set(self.cleaned_data["users"])

        if self.cleaned_data["can_view_past_event"]:
            assign_perm("event_management.view_past_event", group)
        else:
            remove_perm("event_management.view_past_event", group)

        remove_perm("publish_event_for_group", group, Group.objects.all())
        if self.cleaned_data["can_add_event"]:
            assign_perm("event_management.add_event", group)
            assign_perm("event_management.delete_event", group)
            assign_perm(
                "publish_event_for_group", group, self.cleaned_data["publish_event_for_group"]
            )
        else:
            remove_perm("event_management.add_event", group)
            remove_perm("event_management.delete_event", group)

        if self.cleaned_data["can_manage_user"]:
            assign_perm("user_management.add_userprofile", group)
            assign_perm("user_management.change_userprofile", group)
            assign_perm("user_management.delete_userprofile", group)
            assign_perm("user_management.view_userprofile", group)
        else:
            remove_perm("user_management.add_userprofile", group)
            remove_perm("user_management.change_userprofile", group)
            remove_perm("user_management.delete_userprofile", group)
            remove_perm("user_management.view_userprofile", group)

        if self.cleaned_data["can_manage_group"]:
            assign_perm("auth.add_group", group)
            assign_perm("auth.change_group", group)
            assign_perm("auth.delete_group", group)
            assign_perm("auth.view_group", group)
        else:
            remove_perm("auth.add_group", group)
            remove_perm("auth.change_group", group)
            remove_perm("auth.delete_group", group)
            remove_perm("auth.view_group", group)

        return group


class UserProfileForm(ModelForm):
    groups = ModelMultipleChoiceField(
        label=_("Groups"), queryset=Group.objects.all(), widget=Select2MultipleWidget
    )

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
        userprofile.groups.set(self.cleaned_data["groups"])
        userprofile.save()
        return userprofile


class QualificationGrantForm(ModelForm):
    model = QualificationGrant

    class Meta:
        fields = ["qualification", "expires"]
        widgets = {"qualification": Select2Widget, "expires": CustomDateInput(format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            # Hide the field and simply display the qualification name in the template
            self.fields["qualification"].disabled = True
            self.fields["qualification"].widget = forms.HiddenInput()
            self.fields["qualification"].title = instance.qualification.title


QualificationGrantFormset = inlineformset_factory(
    UserProfile,
    QualificationGrant,
    form=QualificationGrantForm,
    extra=0,
)
