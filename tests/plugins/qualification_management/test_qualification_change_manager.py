import uuid

from ephios.core.models import Qualification, QualificationCategory
from ephios.core.services.qualification import collect_all_included_qualifications
from ephios.plugins.qualification_management.importing import QualificationChangeManager


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
    assert set(
        collect_all_included_qualifications([
            Qualification.objects.get(uuid=deserialized_qualifications[2].object.uuid)
        ])
    ) == set(Qualification.objects.all())


def test_importing_cycle_does_not_raise(deserialized_qualifications):
    b, s, g = deserialized_qualifications
    b.m2m_data["includes"].append(g.object.uuid)
    QualificationChangeManager().add_deserialized_qualifications_to_db(
        *deserialized_qualifications
    ).commit()
    assert Qualification.includes.through.objects.count() == 3
    for q in deserialized_qualifications:
        assert set(
            collect_all_included_qualifications([Qualification.objects.get(uuid=q.object.uuid)])
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
    assert set(
        collect_all_included_qualifications([Qualification.objects.get(uuid=g.object.uuid)])
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
