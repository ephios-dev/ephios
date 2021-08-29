import json
import urllib

from crispy_forms.bootstrap import FormActions, Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from django import forms
from django.core import serializers
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.models import Qualification, QualificationCategory
from ephios.extra.crispy import AbortLink


def maybe_deferred_category_uuid_from_deserialized_qualification(deserialized_qualification):
    # category foreign key is deferred as a natural key tuple of (uuid, title)
    try:
        return deserialized_qualification.deferred_fields[Qualification.category.field][0]
    except KeyError:
        # the category was not deferred as it already exists
        return str(deserialized_qualification.object.category.uuid)


def fetch_qualification_repo_objects():
    repo_urls = json.loads(
        global_preferences_registry.manager().get("general__qualification_management_repos")
    )
    for repo_url in repo_urls:
        with urllib.request.urlopen(repo_url) as request:
            yield from serializers.deserialize("json", request, handle_forward_references=True)


def remove_qualification_node(uuid):
    """
    Remove a qualification from the db, filling gaps in the inclusion graph.
    """
    qualification = Qualification.objects.get(uuid=uuid)
    children = list(qualification.included_qualifications.all())
    for parent in qualification.included_by.all():
        parent.included_qualifications.add(*children)

    qualification.delete()


@transaction.atomic()
def store_deserialized_qualification_objects(qualifications, categories):
    """
    Store the deserialized qualifications (a list of tuples of (deserialized object, enabled boolean),
    keeping the ones marked enabled as well as corresponding categories.

    Instead building the inclusion graph, first import everything to have the complete graph in the db.
    Then delete the disabled qualifications, filling the gaps in the graph.
    """

    # To keep the inclusion graph intact, here's what to look out for:
    #   check that newly added qualifications are included in the correct existing ones
    #   check that newly added qualifications include the correct existing ones
    #   check that removing a qualification does not break a chain of inclusion
    #   check that adding a subset of a fixture's qualifications keeps all inclusions

    for category in categories:
        category.save()

    for qualification, enabled in qualifications:
        qualification.save()

    for qualification, enabled in qualifications:
        qualification.save_deferred_fields()

    for qualification in (
        qualification for qualification, enabled in qualifications if not enabled
    ):
        remove_qualification_node(qualification.object.uuid)

    # delete unneeded qualifications: those that originate from the repos but don't have associated qualifications in the db
    categories_uuids = {
        maybe_deferred_category_uuid_from_deserialized_qualification(deserialized)
        for deserialized, enabled in qualifications
    }
    QualificationCategory.objects.annotate(qualification_count=Count("qualifications")).filter(
        uuid__in=categories_uuids, qualification_count=0
    ).delete()


class QualificationImportForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qualifications_by_uuid = {}
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
        store_deserialized_qualification_objects(
            qualifications=[
                (qualification, self.cleaned_data[uuid])
                for uuid, qualification in self.qualifications_by_uuid.items()
            ],
            categories=[v["deserialized_object"] for v in self.categories_by_uuid.values()],
        )

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
                self.qualifications_by_uuid[
                    str(deserialized_object.object.uuid)
                ] = deserialized_object

        for deserialized_object in self.qualifications_by_uuid.values():
            uuid = str(deserialized_object.object.uuid)
            field = forms.BooleanField(
                required=False,
                label=deserialized_object.object.title,
                initial=uuid in existing_qualification_uuids,
            )
            category_uuid = maybe_deferred_category_uuid_from_deserialized_qualification(
                deserialized_object
            )
            self.categories_by_uuid[category_uuid]["field_names"].append(uuid)
            self.fields[uuid] = field
