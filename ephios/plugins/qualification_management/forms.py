from crispy_forms.bootstrap import FormActions, Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Fieldset, Layout, Submit
from django import forms
from django.db.models import Exists, OuterRef
from django.forms.formsets import DELETION_FIELD_NAME
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django_select2.forms import Select2MultipleWidget, Select2Widget

from ephios.core.models import Qualification, QualificationCategory, QualificationGrant, UserProfile
from ephios.extra.crispy import AbortLink
from ephios.extra.fields import EndOfDayDateTimeField
from ephios.extra.widgets import CustomDateInput
from ephios.plugins.qualification_management.importing import (
    QualificationChangeManager,
    fetch_deserialized_qualifications_from_repo,
)

# Templates in this plugin are under core/, because Qualification is a core model.


class QualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = ["title", "uuid", "abbreviation", "category", "includes"]
        widgets = {"includes": Select2MultipleWidget}
        help_texts = {
            "uuid": _(
                "Used to identify qualifications accross the ephios ecosystem. Only change if you know what you are doing."
            )
        }


class QualificationDeleteForm(forms.Form):
    fix_inclusions = forms.BooleanField(
        label=_("Maintain transitive inclusion"),
        initial=True,
        required=False,
    )
    move_grants_to_other_qualifications = forms.ModelMultipleChoiceField(
        label=_("Migrate users to other qualification"),
        required=False,
        widget=Select2MultipleWidget,
        queryset=Qualification.objects.none(),
    )

    @cached_property
    def _active_grants(self):
        return self.qualification.grants.unexpired()

    def __init__(self, *args, **kwargs):
        self.qualification = kwargs.pop("instance")
        super().__init__(*args, **kwargs)
        self.fields["fix_inclusions"].help_text = _(
            "If checked, superior qualifications ({superior}) will include inferior ({inferior}) qualifications."
        ).format(
            superior=", ".join(map(str, self.qualification.included_by.all())) or _("none"),
            inferior=", ".join(map(str, self.qualification.includes.all())) or _("none"),
        )

        self.fields["move_grants_to_other_qualifications"].queryset = Qualification.objects.exclude(
            pk=self.qualification.pk
        )
        help_text = _(
            "Select qualifications to apply to users with the qualification about to be deleted. Expiration dates will be kept."
        )

        if count := self._active_grants.count():
            help_text += " "
            help_text += ngettext(
                "There is {count} user with this qualification.",
                "There are {count} users with this qualification.",
                count,
            ).format(count=count)

        self.fields["move_grants_to_other_qualifications"].help_text = help_text

    def _move_users_to_other_qualifications(self):
        new_grants = []
        for new_qualification in self.cleaned_data["move_grants_to_other_qualifications"]:
            for old_grant in self._active_grants:
                new_grants.append(
                    QualificationGrant(
                        user_id=old_grant.user_id,
                        qualification_id=new_qualification.id,
                        expires=old_grant.expires,
                    )
                )
        QualificationGrant.objects.bulk_create(new_grants)

    def save(self):
        assert self.is_valid()
        self._move_users_to_other_qualifications()
        if self.cleaned_data["fix_inclusions"]:
            manager = QualificationChangeManager()
            manager.remove_qualifications_from_db_fixing_inclusion(self.qualification)
            manager.commit()
        else:
            self.qualification.delete()


class QualificationImportForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deserialized_qualifications_by_uuid = {}
        self.categories_by_uuid = {}
        self.add_qualification_fields()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            TabHolder(
                *[
                    Tab(category["object"].title, *category["field_names"])
                    for category in self.categories_by_uuid.values()
                ]
            ),
            FormActions(
                Submit("submit", _("Save"), css_class="float-end"),
                AbortLink(href=reverse("qualification_management:settings_qualification_list")),
            ),
        )

    def save(self):
        assert self.is_valid()
        manager = QualificationChangeManager()
        for uuid, deserialized_qualification in self.deserialized_qualifications_by_uuid.items():
            if self.cleaned_data[uuid]:
                manager.add_deserialized_qualifications_to_db(deserialized_qualification)
            else:
                manager.add_inclusions_of_deserialized_qualifications(deserialized_qualification)
        manager.commit()

    def add_qualification_fields(self):
        existing_qualification_uuids = {
            str(uuid) for uuid in Qualification.objects.all().values_list("uuid", flat=True)
        }
        for deserialized_qualification in fetch_deserialized_qualifications_from_repo():
            self.categories_by_uuid[str(deserialized_qualification.category.uuid)] = {
                "object": deserialized_qualification.category,
                "field_names": [],
            }
            self.deserialized_qualifications_by_uuid[
                str(deserialized_qualification.object.uuid)
            ] = deserialized_qualification

        for deserialized_qualification in self.deserialized_qualifications_by_uuid.values():
            uuid = str(deserialized_qualification.object.uuid)
            field = forms.BooleanField(
                required=False,
                label=deserialized_qualification.object.title,
                initial=uuid in existing_qualification_uuids,
                disabled=uuid in existing_qualification_uuids,
            )
            self.categories_by_uuid[str(deserialized_qualification.category.uuid)][
                "field_names"
            ].append(uuid)
            self.fields[uuid] = field


class BaseQualificationCategoryFormset(forms.BaseModelFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        initial_form_count = self.initial_form_count()
        if self.can_delete and (self.can_delete_extra or index < initial_form_count):
            category: QualificationCategory = form.instance
            form.fields[DELETION_FIELD_NAME] = forms.BooleanField(
                label=_("Delete"),
                required=False,
                disabled=category.pk and category.qualifications.exists(),
            )


QualificationCategoryFormset = forms.modelformset_factory(
    QualificationCategory,
    formset=BaseQualificationCategoryFormset,
    can_delete=True,
    extra=0,
    fields=["title", "show_with_user", "uuid"],
)


class QualificationReassignmentForm(forms.Form):
    current_qualifications = forms.ModelMultipleChoiceField(
        label=_("current qualifications"),
        queryset=Qualification.objects.all(),
        help_text=_("Only users with all these qualifications will be selected."),
        widget=Select2MultipleWidget,
    )
    new_qualification = forms.ModelChoiceField(
        label=_("qualification to assign"),
        queryset=Qualification.objects.all(),
        widget=Select2Widget,
    )
    expires = EndOfDayDateTimeField(
        label=_("expires"),
        required=False,
        widget=CustomDateInput,
        help_text=_(
            "If empty, the new qualification will not expire. This will only be applied if a user does not already have the target qualification."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(_("User selection"), "current_qualifications"),
            Fieldset(
                _("New qualification"),
                "new_qualification",
                "expires",
            ),
            FormActions(
                Submit("submit", _("Execute"), css_class="float-end"),
                AbortLink(href=reverse("qualification_management:settings_qualification_list")),
            ),
        )

    def perform_reassignment(self):
        assert self.is_valid()
        users = UserProfile.objects.filter(
            *[
                Exists(
                    QualificationGrant.objects.unexpired().filter(
                        qualification=qualification, user=OuterRef("pk")
                    )
                )
                for qualification in self.cleaned_data["current_qualifications"]
            ]
        )
        created_count = 0
        for user in users:
            _, created = QualificationGrant.objects.get_or_create(
                user=user,
                qualification=self.cleaned_data["new_qualification"],
                defaults={"expires": self.cleaned_data["expires"]},
            )
            created_count += int(created)
        return created_count, len(users)
