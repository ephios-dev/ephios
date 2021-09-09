import uuid

import pytest

from ephios.core.models import Qualification, QualificationCategory
from ephios.plugins.qualification_management.importing import (
    DeserializedQualification,
    QualificationChangeManager,
)


@pytest.fixture
def deserialized_qualifications():
    b = DeserializedQualification(
        {
            "uuid": "247fab6a-8784-4976-a406-985fe47dc683",
            "title": "Deutsches Rettungsschwimmabzeichen Bronze",
            "abbreviation": "DRSA Bronze",
            "includes": [],
            "included_by": ["ef95a854-2eeb-431c-a795-bc291b341d49"],
            "category": {
                "uuid": "cd10e68f-41fe-4ca0-a624-3ab3eb85bd08",
                "title": "Wasserrettung Allgemein",
            },
        }
    )
    s = DeserializedQualification(
        {
            "uuid": "ef95a854-2eeb-431c-a795-bc291b341d49",
            "title": "Deutsches Rettungsschwimmabzeichen Silber",
            "abbreviation": "DRSA Silber",
            "includes": ["247fab6a-8784-4976-a406-985fe47dc683"],
            "included_by": ["b601a18b-cee8-4037-af33-dd7aabeac295"],
            "category": {
                "uuid": "cd10e68f-41fe-4ca0-a624-3ab3eb85bd08",
                "title": "Wasserrettung Allgemein",
            },
        }
    )
    g = DeserializedQualification(
        {
            "uuid": "b601a18b-cee8-4037-af33-dd7aabeac295",
            "title": "Deutsches Rettungsschwimmabzeichen Gold",
            "abbreviation": "DRSA Gold",
            "includes": ["ef95a854-2eeb-431c-a795-bc291b341d49"],
            "included_by": [],
            "category": {
                "uuid": "cd10e68f-41fe-4ca0-a624-3ab3eb85bd08",
                "title": "Wasserrettung Allgemein",
            },
        }
    )
    return b, s, g


@pytest.fixture
def saved_deserialized_qualifications(deserialized_qualifications):
    QualificationChangeManager().add_deserialized_qualifications_to_db(
        *deserialized_qualifications
    ).commit()
    return deserialized_qualifications


def test_plain_import(deserialized_qualifications):
    assert not QualificationCategory.objects.exists()
    QualificationChangeManager().add_deserialized_qualifications_to_db(
        *deserialized_qualifications
    ).commit()
    assert QualificationCategory.objects.count() == 1
    assert set(Qualification.objects.all().values_list("uuid", flat=True)) == {
        uuid.UUID(q.object.uuid) for q in deserialized_qualifications
    }

    # assert inclusion
    assert Qualification.includes.through.objects.count() == 2
    assert Qualification.collect_all_included_qualifications(
        [Qualification.objects.get(uuid=deserialized_qualifications[2].object.uuid)]
    ) == set(Qualification.objects.all())


def test_importing_cycle_does_not_raise(deserialized_qualifications):
    b, s, g = deserialized_qualifications
    b.m2m_data["includes"].append(g.object.uuid)
    QualificationChangeManager().add_deserialized_qualifications_to_db(
        *deserialized_qualifications
    ).commit()
    assert Qualification.includes.through.objects.count() == 3
    for q in deserialized_qualifications:
        assert Qualification.collect_all_included_qualifications(
            [Qualification.objects.get(uuid=q.object.uuid)]
        ) == set(Qualification.objects.all())


def test_removing_from_cycle_does_not_raise(deserialized_qualifications):
    b, s, g = deserialized_qualifications
    b.m2m_data["includes"].append(g.object.uuid)
    QualificationChangeManager().add_deserialized_qualifications_to_db(
        *deserialized_qualifications
    ).commit()

    QualificationChangeManager().remove_qualifications_from_db_fixing_inclusion(
        Qualification.objects.get(uuid=b.object.uuid)
    ).commit()
    assert Qualification.includes.through.objects.count() == 2
    QualificationChangeManager().remove_qualifications_from_db_fixing_inclusion(
        Qualification.objects.get(uuid=s.object.uuid)
    ).commit()
    assert Qualification.includes.through.objects.count() == 1
    QualificationChangeManager().remove_qualifications_from_db_fixing_inclusion(
        Qualification.objects.get()
    ).commit()


def test_import_with_inclusion_support_creates_inclusion(deserialized_qualifications):
    b, s, g = deserialized_qualifications
    QualificationChangeManager().add_deserialized_qualifications_to_db(
        b, g
    ).add_inclusions_of_deserialized_qualifications(s).commit()
    assert Qualification.objects.count() == 2
    assert set(Qualification.objects.get(uuid=g.object.uuid).includes.all()) == {
        Qualification.objects.get(uuid=b.object.uuid)
    }


def test_removing_qualification_keeps_inclusion(saved_deserialized_qualifications):
    b, s, g = saved_deserialized_qualifications
    QualificationChangeManager().remove_qualifications_from_db_fixing_inclusion(
        Qualification.objects.get(uuid=s.object.uuid)
    ).commit()

    assert Qualification.objects.count() == 2
    assert set(Qualification.objects.get(uuid=g.object.uuid).includes.all()) == {
        Qualification.objects.get(uuid=b.object.uuid)
    }


def test_reimporting_clears_existing_wrong_inclusions(saved_deserialized_qualifications):
    b, s, g = saved_deserialized_qualifications
    Qualification.objects.get(uuid=g.object.uuid).includes.add(
        Qualification.objects.get(uuid=b.object.uuid)
    )
    assert Qualification.includes.through.objects.count() == 3
    QualificationChangeManager().add_deserialized_qualifications_to_db(
        *saved_deserialized_qualifications
    ).commit()

    assert Qualification.includes.through.objects.count() == 2
    assert Qualification.collect_all_included_qualifications(
        [Qualification.objects.get(uuid=g.object.uuid)]
    ) == set(Qualification.objects.all())


def test_reimporting_doesnt_change_category(saved_deserialized_qualifications):
    other_category = QualificationCategory.objects.create(
        title="other", uuid="3d6696b0-1b49-4065-9d3e-c648ec2b6239"
    )
    qualification = Qualification.objects.first()
    qualification.category = other_category
    qualification.save()

    QualificationChangeManager().add_deserialized_qualifications_to_db(
        *saved_deserialized_qualifications
    ).commit()
    assert Qualification.objects.first().category == other_category
