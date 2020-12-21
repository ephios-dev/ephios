from datetime import datetime

import pytest

from ephios.user_management.consequences import QualificationConsequenceHandler


@pytest.fixture
def qualifications_consequence(volunteer, qualifications, event, tz):
    return QualificationConsequenceHandler.create(
        user=volunteer,
        shift=event.shifts.first(),
        qualification=qualifications.nfs,
        expires=datetime(2064, 4, 1).astimezone(tz),
    )


@pytest.mark.django_db
def test_render_qualification_granting(qualifications_consequence):
    assert qualifications_consequence.render()


@pytest.mark.django_db
def test_confirm_qualification_granting(superuser, qualifications_consequence, qualifications):
    assert qualifications.nfs not in qualifications_consequence.user.qualifications
    qualifications_consequence.confirm(superuser)
    assert qualifications.nfs in qualifications_consequence.user.qualifications
