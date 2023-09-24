import itertools
import urllib
from typing import Dict
from urllib.error import URLError

from django.db import transaction
from django.db.models import Count
from dynamic_preferences.registries import global_preferences_registry
from rest_framework.exceptions import ValidationError as RestValidationError
from rest_framework.parsers import JSONParser

from ephios.core.models import Qualification, QualificationCategory
from ephios.core.services.qualification import DirectedGraph
from ephios.plugins.qualification_management.serializers import QualificationFixtureSerializer


class DeserializedQualification:
    def __init__(self, validated_data):
        self.m2m_data = {
            "includes": validated_data["includes"],
            "included_by": validated_data["included_by"],
        }
        self.object = Qualification(
            **{key: validated_data[key] for key in ("title", "abbreviation", "uuid")},
        )
        self.category = QualificationCategory(
            **{key: validated_data["category"][key] for key in ("title", "uuid")},
        )

    def __hash__(self):
        return hash(self.object.uuid)


class RepoError(Exception):
    pass


def fetch_deserialized_qualifications_from_repo():
    repo_urls = (
        stripped_url
        for url in global_preferences_registry.manager()
        .get("general__qualification_management_repos")
        .splitlines()
        if (stripped_url := url.strip())
    )
    try:
        for repo_url in repo_urls:
            with urllib.request.urlopen(repo_url) as request:
                data = JSONParser().parse(request)
                serializer = QualificationFixtureSerializer(data=data, many=True)
                assert serializer.is_valid(raise_exception=True)
                yield from (DeserializedQualification(d) for d in serializer.validated_data)
    except (URLError, RestValidationError) as e:
        raise RepoError from e


class QualificationChangeManager:
    def __init__(self):
        self.deserialized_qualifications_to_add = set()
        self.inclusion_supporting_deserialized_qualifications = set()
        self.qualifications_to_delete_fixing_inclusion = set()

        self.existing_qualifications_by_uuid: Dict[str, Qualification] = {
            str(obj.uuid): obj for obj in Qualification.objects.all()
        }

    def add_deserialized_qualifications_to_db(self, *deserialized_qualifications):
        self.deserialized_qualifications_to_add |= set(deserialized_qualifications)
        return self

    def add_inclusions_of_deserialized_qualifications(self, *deserialized_qualifications):
        self.inclusion_supporting_deserialized_qualifications |= set(deserialized_qualifications)
        return self

    def remove_qualifications_from_db_fixing_inclusion(self, *qualifications):
        self.qualifications_to_delete_fixing_inclusion |= set(qualifications)
        return self

    def _attach_deferred_categories_to_deserialized_qualifications(self):
        categories_by_uuid = {str(c.uuid): c for c in QualificationCategory.objects.all()}
        for deserialized_qualification in self.deserialized_qualifications_to_add:
            deserialized_qualification.object.category = categories_by_uuid[
                str(deserialized_qualification.category.uuid)
            ]

    def _build_inclusion_graph(self):
        graph = DirectedGraph()
        # add qualifications from the repo
        for deserialized_qualification in itertools.chain(
            self.deserialized_qualifications_to_add,
            self.inclusion_supporting_deserialized_qualifications,
        ):
            this_uuid = str(deserialized_qualification.object.uuid)
            inclusions = set(deserialized_qualification.m2m_data["includes"])
            graph.add(node=this_uuid, children=inclusions)
            for included_by in deserialized_qualification.m2m_data["included_by"]:
                graph.add(node=str(included_by), children={str(this_uuid)})

        # add existing qualifications and their inclusions
        repository_qualification_uuids = set(graph.adjancent_nodes.keys())
        for qualification in self.existing_qualifications_by_uuid.values():
            this_uuid = str(qualification.uuid)
            inclusions = {str(included.uuid) for included in qualification.includes.all()}
            if this_uuid in repository_qualification_uuids:
                # This existing qualification is also part of the repo.
                # Inclusions to other repo qualifications, that are originally not part of the repo should not be reproduced, so we don't add them.
                inclusions -= repository_qualification_uuids
            graph.add(node=this_uuid, children=inclusions)

        # now remove supporting-only repo qualifications and explicitly removed ones, maintaining graph connectivity
        for deserialized_qualification in self.inclusion_supporting_deserialized_qualifications:
            graph.remove_node(str(deserialized_qualification.object.uuid))
        for qualification in self.qualifications_to_delete_fixing_inclusion:
            graph.remove_node(str(qualification.uuid))

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
                deserialized_qualification.object.save()
                self.existing_qualifications_by_uuid[uuid] = deserialized_qualification.object

        # Finally, set m2m inclusions
        for uuid, inclusions in self.graph.adjancent_nodes.items():
            qualification = self.existing_qualifications_by_uuid[uuid]
            qualification.includes.set(
                [self.existing_qualifications_by_uuid[inclusion] for inclusion in inclusions]
            )

    def _prepare_qualification_category_db(self):
        uuids_of_used_categories = {
            str(deserialized_qualification.category.uuid)
            for deserialized_qualification in self.deserialized_qualifications_to_add
        }
        qualification_categories = {
            deserialized_qualifcation.category.uuid: deserialized_qualifcation.category
            for deserialized_qualifcation in self.deserialized_qualifications_to_add
        }
        for category in qualification_categories.values():
            if str(category.uuid) in uuids_of_used_categories:
                QualificationCategory.objects.get_or_create(
                    uuid=category.uuid,
                    defaults={"title": category.title},
                )

    def _delete_unneeded_qualification_categories(self):
        repo_categories_uuids = {
            str(deserialized_qualifications.category.uuid)
            for deserialized_qualifications in itertools.chain(
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
