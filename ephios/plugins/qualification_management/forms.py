from crispy_forms.bootstrap import FormActions, Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django_select2.forms import Select2MultipleWidget

from ephios.core.models import Qualification, QualificationCategory, QualificationGrant
from ephios.extra.crispy import AbortLink
from ephios.plugins.qualification_management.importing import (
    QualificationChangeManager,
    fetch_qualification_repo_objects,
    maybe_deferred_category_uuid_from_deserialized_qualification,
)

# Templates in this plugin are under core/, because Qualification is a core model.


class QualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = ["title", "uuid", "abbreviation", "category", "included_qualifications"]
        widgets = {"included_qualifications": Select2MultipleWidget}
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
    move_grants_to_other_qualification = forms.ModelMultipleChoiceField(
        label=_("Migrate users to other qualification"),
        required=False,
        widget=Select2MultipleWidget,
        queryset=Qualification.objects.none(),
    )

    @cached_property
    def _active_grants(self):
        return self.qualification.grants.exclude(expires__isnull=False, expires__lt=now())

    def __init__(self, *args, **kwargs):
        self.qualification = kwargs.pop("instance")
        super().__init__(*args, **kwargs)
        self.fields["fix_inclusions"].help_text = _(
            "If checked, superior qualifications ({superior}) will include inferior ({inferior}) qualifications."
        ).format(
            superior=", ".join(map(str, self.qualification.included_by.all())) or _("none"),
            inferior=", ".join(map(str, self.qualification.included_qualifications.all()))
            or _("none"),
        )

        self.fields["move_grants_to_other_qualification"].queryset = Qualification.objects.exclude(
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

        self.fields["move_grants_to_other_qualification"].help_text = help_text

    def _move_users_to_other_qualifications(self):
        new_grants = []
        for new_qualification in self.cleaned_data["move_grants_to_other_qualification"]:
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
                    Tab(category["deserialized_object"].object.title, *category["field_names"])
                    for category in self.categories_by_uuid.values()
                ]
            ),
            FormActions(
                Submit("submit", _("Save"), css_class="float-end"),
                AbortLink(href=reverse("qualification_management:settings_qualification_list")),
            ),
        )

    def save(self):
        if not self.is_valid():
            raise ValidationError("Form is not valid")

        manager = QualificationChangeManager()
        manager.add_deserialized_qualification_categories(
            *[v["deserialized_object"] for v in self.categories_by_uuid.values()]
        )
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
        for deserialized_object in fetch_qualification_repo_objects():
            if isinstance(deserialized_object.object, QualificationCategory):
                self.categories_by_uuid[str(deserialized_object.object.uuid)] = {
                    "deserialized_object": deserialized_object,
                    "field_names": [],
                }
            else:
                self.deserialized_qualifications_by_uuid[
                    str(deserialized_object.object.uuid)
                ] = deserialized_object

        for deserialized_object in self.deserialized_qualifications_by_uuid.values():
            uuid = str(deserialized_object.object.uuid)
            field = forms.BooleanField(
                required=False,
                label=deserialized_object.object.title,
                initial=uuid in existing_qualification_uuids,
                disabled=uuid in existing_qualification_uuids,
            )
            category_uuid = maybe_deferred_category_uuid_from_deserialized_qualification(
                deserialized_object
            )
            self.categories_by_uuid[category_uuid]["field_names"].append(uuid)
            self.fields[uuid] = field
