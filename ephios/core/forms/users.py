from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit
from django import forms
from django.contrib.auth.models import Group
from django.forms import (
    BooleanField,
    CharField,
    DateField,
    DecimalField,
    Form,
    ModelForm,
    ModelMultipleChoiceField,
    inlineformset_factory,
)
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget, Select2Widget
from guardian.shortcuts import assign_perm, get_objects_for_group, remove_perm

from ephios.core.consequences import WorkingHoursConsequenceHandler
from ephios.core.models import QualificationGrant, UserProfile
from ephios.core.widgets import MultiUserProfileWidget
from ephios.extra.widgets import CustomDateInput


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
        help_text=_(
            "If checked, users in this group can add and edit all groups, their permissions as well as group memberships."
        ),
        required=False,
    )
    users = ModelMultipleChoiceField(
        label=_("Users"), queryset=UserProfile.objects.all(), widget=MultiUserProfileWidget
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
                "decide_workinghours_for_group": get_objects_for_group(
                    group, "decide_workinghours_for_group", klass=Group
                ),
                **kwargs.get("initial", {}),
            }
        super().__init__(**kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("name"),
            Field("users"),
            Field("can_manage_user"),
            Field("can_manage_group"),
            Field("can_view_past_event"),
            Field("decide_workinghours_for_group"),
            Field("can_add_event"),
            Field("publish_event_for_group", wrapper_class="publish-select"),
            FormActions(Submit("submit", "Submit")),
        )

    def save(self, commit=True):
        group = super().save(commit)

        group.user_set.set(self.cleaned_data["users"])

        if self.cleaned_data["can_view_past_event"]:
            assign_perm("core.view_past_event", group)
        else:
            remove_perm("core.view_past_event", group)

        remove_perm("publish_event_for_group", group, Group.objects.all())
        if self.cleaned_data["can_add_event"]:
            assign_perm("core.add_event", group)
            assign_perm("core.delete_event", group)
            assign_perm(
                "publish_event_for_group", group, self.cleaned_data["publish_event_for_group"]
            )
        else:
            remove_perm("core.add_event", group)
            remove_perm("core.delete_event", group)

        if self.cleaned_data["can_manage_user"]:
            assign_perm("core.add_userprofile", group)
            assign_perm("core.change_userprofile", group)
            assign_perm("core.delete_userprofile", group)
            assign_perm("core.view_userprofile", group)
        else:
            remove_perm("core.add_userprofile", group)
            remove_perm("core.change_userprofile", group)
            remove_perm("core.delete_userprofile", group)
            remove_perm("core.view_userprofile", group)

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

        if "decide_workinghours_for_group" in self.changed_data:
            remove_perm("decide_workinghours_for_group", group, Group.objects.all())
            assign_perm(
                "decide_workinghours_for_group",
                group,
                self.cleaned_data["decide_workinghours_for_group"],
            )

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
        if request and request.user.has_perm("auth.change_group"):
            self.fields["groups"].disabled = False
        else:
            self.fields["groups"].help_text = _("You are not allowed to change group associations.")

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
