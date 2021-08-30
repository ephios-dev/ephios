import itertools
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
        # inclusions is a dict where keys are nodes and values are lists of nodes the key node has an edge of inclusion to
        self.inclusions = defaultdict(set)

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


class QualificationChangeManager:
    def __init__(self):
        self.deserialized_qualification_categories = set()
        self.deserialized_qualifications_to_add = set()
        self.inclusion_supporting_deserialized_qualifications = set()
        self.qualifications_to_delete_fixing_inclusion = set()

        self.existing_qualifications_by_uuid: Dict[str, Qualification] = {
            str(obj.uuid): obj for obj in Qualification.objects.all()
        }

    def add_deserialized_qualification_categories(self, *deserialized_qualification_categories):
        self.deserialized_qualification_categories |= set(deserialized_qualification_categories)

    def add_deserialized_qualifications_to_db(self, *deserialized_qualifications):
        self.deserialized_qualifications_to_add |= set(deserialized_qualifications)

    def add_inclusions_of_deserialized_qualifications(self, *deserialized_qualifications):
        self.inclusion_supporting_deserialized_qualifications |= set(deserialized_qualifications)

    def remove_qualifications_from_db_fixing_inclusion(self, *qualifications):
        self.qualifications_to_delete_fixing_inclusion |= set(qualifications)

    def _qualifications_by_pk(self, pk):
        # this should probably be cached in some way
        return {obj.id: obj for obj in self.existing_qualifications_by_uuid.values()}[pk]

    def _attach_deferred_categories_to_deserialized_qualifications(self):
        categories_by_uuid = {str(c.uuid): c for c in QualificationCategory.objects.all()}
        for deserialized in self.deserialized_qualifications_to_add:
            category_uuid = maybe_deferred_category_uuid_from_deserialized_qualification(
                deserialized
            )
            deserialized.object.category = categories_by_uuid[category_uuid]

    def _build_inclusion_graph(self):
        graph = QualificationGraph()
        # add qualifications from the repo
        for deserialized_qualification in itertools.chain(
            self.deserialized_qualifications_to_add,
            self.inclusion_supporting_deserialized_qualifications,
        ):
            # inclusions might be saved in m2m_data or deferred_fields, depending on whether referenced objects already exist
            # deferred_fields contains a list of natural key tuples of (uuid, title)
            inclusions = {
                str(value[0])
                for value in deserialized_qualification.deferred_fields.get(
                    Qualification.included_qualifications.field, []
                )
            }
            inclusions |= {
                str(self._qualifications_by_pk(pk).uuid)
                for pk in deserialized_qualification.m2m_data.get("included_qualifications", [])
            }
            graph.add_qualification(
                uuid=str(deserialized_qualification.object.uuid), inclusions=inclusions
            )

        # add existing qualifications and their inclusions
        repository_qualification_uuids = set(graph.inclusions.keys())
        for qualification in self.existing_qualifications_by_uuid.values():
            uuid = str(qualification.uuid)
            inclusions = {
                str(included.uuid) for included in qualification.included_qualifications.all()
            }
            if uuid in repository_qualification_uuids:
                # This existing qualification is also part of the repo.
                # Inclusions to other repo qualifications, that are originally not part of the repo should not be reproduced, so we don't add them.
                inclusions -= repository_qualification_uuids
            graph.add_qualification(uuid=uuid, inclusions=inclusions)

        # now remove supporting-only repo qualifications and explicitly removed ones, maintaining graph connectivity
        for deserialized_qualification in self.inclusion_supporting_deserialized_qualifications:
            graph.remove_qualification(str(deserialized_qualification.object.uuid))
        for qualification in self.qualifications_to_delete_fixing_inclusion:
            graph.remove_qualification(str(qualification.uuid))

        self.graph = graph

    def _perform_qualification_db_operations(self):
        # Delete the qualifications we don't need.
        Qualification.objects.filter(
            pk__in={obj.pk for obj in self.qualifications_to_delete_fixing_inclusion}
        ).delete()

        # Create not yet existing qualification objects (without m2m inclusion data)
        for deserialized_qualification in self.deserialized_qualifications_to_add:
            uuid = str(deserialized_qualification.object.uuid)
            if uuid not in self.existing_qualifications_by_uuid:
                deserialized_qualification.save(save_m2m=False)
                self.existing_qualifications_by_uuid[uuid] = deserialized_qualification.object

        # Finally, set m2m inclusions
        for uuid, inclusions in self.graph.inclusions.items():
            qualification = self.existing_qualifications_by_uuid[uuid]
            qualification.included_qualifications.set(
                [self.existing_qualifications_by_uuid[inclusion] for inclusion in inclusions]
            )

    def _prepare_qualification_category_db(self):
        uuid_of_used_categories = {
            maybe_deferred_category_uuid_from_deserialized_qualification(deserialized_object)
            for deserialized_object in self.deserialized_qualifications_to_add
        }
        for deserialized_category in self.deserialized_qualification_categories:
            if str(deserialized_category.object.uuid) in uuid_of_used_categories:
                deserialized_category.save()

    def _delete_unneeded_qualification_categories(self):
        repo_categories_uuids = {
            maybe_deferred_category_uuid_from_deserialized_qualification(deserialized_category)
            for deserialized_category in itertools.chain(
                self.deserialized_qualifications_to_add,
                self.inclusion_supporting_deserialized_qualifications,
            )
        }
        QualificationCategory.objects.annotate(qualification_count=Count("qualifications")).filter(
            uuid__in=repo_categories_uuids, qualification_count=0
        ).delete()

    @transaction.atomic()
    def commit(self):
        # To keep the inclusion graph intact, here's what to look out for:
        # - check that newly added qualifications are included in the correct existing ones
        # - check that newly added qualifications include the correct existing ones
        # - check that removing a qualification does not break a chain of inclusion
        # - check that adding a subset of a fixture's qualifications keeps all inclusions

        self.inclusion_supporting_deserialized_qualifications -= (
            self.deserialized_qualifications_to_add
        )

        self._prepare_qualification_category_db()
        self._attach_deferred_categories_to_deserialized_qualifications()
        self._build_inclusion_graph()
        self._perform_qualification_db_operations()
        self._delete_unneeded_qualification_categories()


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
