import json
import urllib
from collections import defaultdict
from typing import Dict

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


class QualificationGraph:
    """Class used to compute the inclusions used in the qualification graph."""

    def __init__(self):
        self.inclusions = defaultdict(set)
        self.removed = []

    def add_qualification(self, uuid, inclusions, expand_existing=True):
        """Add a new qualification to the graph."""
        if not expand_existing:
            if uuid in self.inclusions.keys():
                raise ValueError("That uuid already exists.")
            self.inclusions[uuid] = inclusions
        else:
            self.inclusions[uuid] |= inclusions

    def parents(self, child):
        for parent, children in self.inclusions.items():
            if child in children:
                yield parent

    def remove_qualification(self, uuid):
        """Remove a qualification, keeping the inclusions intact."""
        children = self.inclusions[uuid]
        for parent in self.parents(uuid):
            self.inclusions[parent] |= children
            self.inclusions[parent].remove(uuid)
        del self.inclusions[uuid]
        self.removed.append(uuid)


def build_qualifications_db_state(qualifications):
    """
    Create and delete qualifications to get the db into the state as given by the `qualifications` list of tuples (deserialized object, enabled bool).
    Do not delete qualifications not present in the qualifications list. Adjust inclusion to keep the inclusion graph intact.
    This method expects the needed qualification categories to exist.
    """

    # To keep the inclusion graph intact, here's what to look out for:
    #   check that newly added qualifications are included in the correct existing ones
    #   check that newly added qualifications include the correct existing ones
    #   check that removing a qualification does not break a chain of inclusion
    #   check that adding a subset of a fixture's qualifications keeps all inclusions

    existing_qualifications_by_uuid: Dict[str, Qualification] = {
        str(obj.uuid): obj for obj in Qualification.objects.all()
    }
    existing_qualifications_by_pk: Dict[int, Qualification] = {
        obj.id: obj for obj in existing_qualifications_by_uuid.values()
    }

    # build graph
    graph = QualificationGraph()
    # add qualifications from the repo
    for qualification, enabled in qualifications:
        # inclusions might be saved in m2m_data or deferred_fields, depending on whether referenced objects already exist
        # deferred_fields contains a list of natural key tuples of (uuid, title)
        inclusions = {
            str(value[0])
            for value in qualification.deferred_fields.get(
                Qualification.included_qualifications.field, []
            )
        }
        inclusions |= {
            str(existing_qualifications_by_pk[pk].uuid)
            for pk in qualification.m2m_data.get("included_qualifications", [])
        }
        graph.add_qualification(uuid=str(qualification.object.uuid), inclusions=inclusions)

    # add existing qualifications and their inclusions
    repository_qualification_uuids = set(graph.inclusions.keys())
    for qualification in existing_qualifications_by_uuid.values():
        uuid = str(qualification.uuid)
        inclusions = {
            str(included.uuid) for included in qualification.included_qualifications.all()
        }
        if uuid in repository_qualification_uuids:
            # This existing qualification is also part of the repo.
            # Inclusions to other repo qualifications, that are originally not part of the repo should not be reproduced, so we don't add them.
            inclusions -= repository_qualification_uuids
        graph.add_qualification(uuid=uuid, inclusions=inclusions)

    # now remove disabled repo qualifications, maintaining graph connectivity
    for qualification, enabled in qualifications:
        if not enabled:
            graph.remove_qualification(str(qualification.object.uuid))

    # The graph now contains the exact qualifications and inclusions we need.
    # Delete the qualifications we don't need.
    Qualification.objects.filter(uuid__in=graph.removed).delete()

    # Create not yet existing qualification objects (without m2m inclusion data)
    for deserialized, enabled in qualifications:
        uuid = str(deserialized.object.uuid)
        if enabled and uuid not in existing_qualifications_by_uuid:
            deserialized.save(save_m2m=False)
            existing_qualifications_by_uuid[uuid] = deserialized.object

    # Finally, set m2m inclusions
    for uuid, inclusions in graph.inclusions.items():
        qualification = existing_qualifications_by_uuid[uuid]
        qualification.included_qualifications.set(
            [existing_qualifications_by_uuid[inclusion] for inclusion in inclusions]
        )


def attach_deferred_categories(deserialized_qualifications):
    categories_by_uuid = {str(c.uuid): c for c in QualificationCategory.objects.all()}
    for deserialized in deserialized_qualifications:
        category_uuid = maybe_deferred_category_uuid_from_deserialized_qualification(deserialized)
        deserialized.object.category = categories_by_uuid[category_uuid]


@transaction.atomic()
def store_deserialized_qualification_objects(qualifications, categories):
    """
    Store the deserialized qualifications (a list of tuples of (deserialized object, enabled boolean),
    keeping the ones marked enabled as well as corresponding categories.
    """

    # add needed categories
    uuid_of_used_categories = {
        maybe_deferred_category_uuid_from_deserialized_qualification(deserialized)
        for deserialized, enabled in qualifications
        if enabled
    }
    for category in categories:
        if str(category.object.uuid) in uuid_of_used_categories:
            category.save()

    attach_deferred_categories(
        [qualification for qualification, enabled in qualifications if enabled]
    )
    build_qualifications_db_state(qualifications)

    # delete unneeded categories: those that originate from the repos but don't have associated qualifications in the db
    repo_categories_uuids = {
        maybe_deferred_category_uuid_from_deserialized_qualification(deserialized)
        for deserialized, enabled in qualifications
    }
    QualificationCategory.objects.annotate(qualification_count=Count("qualifications")).filter(
        uuid__in=repo_categories_uuids, qualification_count=0
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
