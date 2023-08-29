import pytest

from ephios.core.models import QualificationGrant
from ephios.core.services.qualification import (
    collect_all_included_qualifications,
    essential_set_of_qualifications,
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


def test_essential_set_of_qualifications(overqualified_volunteer, qualifications):
    essentials = essential_set_of_qualifications(overqualified_volunteer.qualifications.all())
    assert essentials == {qualifications.nfs, qualifications.c, qualifications.be}


def test_collect_all_included_qualifications(qualifications, qualified_volunteer):
    assert set(collect_all_included_qualifications([qualifications.nfs, qualifications.c1e])) == {
        qualifications.c1e,
        qualifications.c1,
        qualifications.be,
        qualifications.b,
        qualifications.nfs,
        qualifications.rs,
    }
