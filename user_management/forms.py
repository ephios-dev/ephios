from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.forms import (
    ModelForm,
    ModelMultipleChoiceField,
    BooleanField,
    SelectMultiple,
    DateField,
)
from django_select2.forms import Select2MultipleWidget
from guardian.shortcuts import assign_perm, remove_perm

from jep.widgets import CustomDateInput
from user_management.models import UserProfile
from django.utils.translation import gettext as _

from user_management.widgets import MultiUserProfileWidget


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    password_validation = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)
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
        queryset=Group.objects.all(),
        required=False,
        help_text=_("Choose groups that this group can make events visible for."),
        widget=Select2MultipleWidget,
    )
    can_view_past_event = BooleanField(required=False, label=_("Can view past events"))
    can_add_event = BooleanField(required=False)
    users = ModelMultipleChoiceField(
        queryset=UserProfile.objects.all(), widget=MultiUserProfileWidget
    )

    field_order = [
        "name",
        "users",
        "can_view_past_event",
        "can_add_event",
        "publish_event_for_group",
    ]

    class Meta:
        model = Group
        fields = ["name"]

    def save(self, commit=True):
        group = super().save(commit)

        group.user_set.set(self.cleaned_data["users"])

        if self.cleaned_data["can_view_past_event"]:
            assign_perm("event_management.view_past_event", group)
        else:
            remove_perm("event_management.view_past_event", group)

        if self.cleaned_data["can_add_event"]:
            assign_perm("event_management.add_event", group)
            assign_perm("event_management.delete_event", group)

            if "publish_event_for_group" in self.changed_data:
                for target_group in self.cleaned_data["publish_event_for_group"].difference(
                    self.initial["publish_event_for_group"]
                ):
                    assign_perm("publish_event_for_group", group, target_group)
                for target_group in self.initial["publish_event_for_group"].difference(
                    self.cleaned_data["publish_event_for_group"]
                ):
                    remove_perm("publish_event_for_group", group, target_group)
        else:
            remove_perm("event_management.add_event", group)
            remove_perm("event_management.delete_event", group)
            for target_group in Group.objects.all():
                remove_perm("publish_event_for_group", group, target_group)


class UserProfileForm(ModelForm):
    groups = ModelMultipleChoiceField(queryset=Group.objects.all(), widget=Select2MultipleWidget)

    class Meta:
        model = UserProfile
        fields = ["email", "first_name", "last_name", "date_of_birth", "phone"]
        widgets = {"date_of_birth": CustomDateInput(format="%Y-%m-%d")}

    def save(self, commit=True):
        userprofile = super().save(commit)

        userprofile.groups.set(self.cleaned_data["groups"])
