from datetime import datetime

import pytest
from django.utils import timezone

from ephios.user_management.models import QualificationGrant


@pytest.fixture
def qualified_volunteer(volunteer, qualifications, tz):
    QualificationGrant.objects.create(
        user=volunteer,
        qualification=qualifications.nfs,
        expires=datetime(2064, 4, 1).astimezone(tz),
    )
    QualificationGrant.objects.create(
        user=volunteer, qualification=qualifications.c, expires=datetime(2090, 4, 1).astimezone(tz)
    )
    QualificationGrant.objects.create(user=volunteer, qualification=qualifications.b, expires=None)
    return volunteer


@pytest.mark.django_db
def test_user_qualifications(qualified_volunteer, qualifications, tz):
    assert timezone.now().year < 2064  # update tests
    assert set(qualified_volunteer.qualifications) == {
        qualifications.nfs,
        qualifications.c,
        qualifications.b,
    }
    assert qualified_volunteer.qualifications.get(id=qualifications.c.id).expires == datetime(
        2090, 4, 1
    ).astimezone(tz)
    assert qualified_volunteer.qualifications.get(id=qualifications.b.id).expires is None
    assert qualified_volunteer.qualifications.get(id=qualifications.nfs.id).expires == datetime(
        2064, 4, 1
    ).astimezone(tz)
