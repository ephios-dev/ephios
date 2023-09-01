import pytest

from ephios.core.models import QualificationCategory, QualificationGrant
from ephios.core.services.qualification import (
    collect_all_included_qualifications,
    essential_set_of_qualifications,
    top_level_set_of_qualifications,
)


@pytest.fixture
def overqualified_volunteer(qualified_volunteer, qualifications):
    for q in [
        qualifications.rs,
        qualifications.c1,
        qualifications.be,
    ]:
        QualificationGrant.objects.create(user=qualified_volunteer, qualification=q)
    return qualified_volunteer


def test_top_level_set_of_qualifications(overqualified_volunteer, qualifications):
    top_level = top_level_set_of_qualifications(overqualified_volunteer.qualifications.all())
    assert top_level == {qualifications.nfs, qualifications.c, qualifications.be}


def test_collect_all_included_qualifications(qualifications, qualified_volunteer):
    assert set(collect_all_included_qualifications([qualifications.nfs, qualifications.c1e])) == {
        qualifications.c1e,
        qualifications.c1,
        qualifications.be,
        qualifications.b,
        qualifications.nfs,
        qualifications.rs,
    }


def test_essential_set_of_qualifications_to_show_with_user(overqualified_volunteer, qualifications):
    essentials = essential_set_of_qualifications(overqualified_volunteer.qualifications.all())
    assert essentials == {qualifications.nfs, qualifications.c, qualifications.be}
    driverslicense_category = qualifications.c.category
    driverslicense_category.show_with_user = False
    driverslicense_category.save()
    essentials = essential_set_of_qualifications(overqualified_volunteer.qualifications.all())
    assert essentials == {qualifications.nfs}


def test_essential_set_of_qualifications_to_show_with_user_with_empty_graph():
    assert not essential_set_of_qualifications([])


def test_essential_set_of_qualifications_to_show_with_user_with_root_removal():
    A = QualificationCategory.objects.create(title="A", show_with_user=True)
    B = QualificationCategory.objects.create(title="B", show_with_user=False)
    a1 = A.qualifications.create(title="a1", category=A)
    b1 = B.qualifications.create(title="b1", category=B)
    b1.includes.add(a1)
    a2 = A.qualifications.create(title="a2", category=A)
    a2.includes.add(b1)
    b2 = B.qualifications.create(title="b2", category=B)
    b2.includes.add(a2)
    assert {a2} == essential_set_of_qualifications([a1, b1, a2, b2])
