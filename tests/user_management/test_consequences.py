from datetime import datetime

import pytest
from django.db.models import OuterRef, Subquery
from django.db.models.fields.json import KeyTransform

from ephios.user_management.consequences import QualificationConsequenceHandler
from ephios.user_management.models import Consequence, Qualification


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
def test_render_qualification_without_shift_information(volunteer, qualifications, tz):
    c = QualificationConsequenceHandler.create(
        user=volunteer,
        qualification=qualifications.nfs,
        expires=datetime(2064, 4, 1).astimezone(tz),
    )
    assert c.render()


@pytest.mark.django_db
def test_annotation_with_json(qualifications_consequence, qualifications):
    qs = (
        Consequence.objects.filter(state=Consequence.States.NEEDS_CONFIRMATION)
        .annotate(qualification_id=KeyTransform("qualification_id", "data"))
        .annotate(
            qualification_title=Subquery(
                Qualification.objects.filter(pk=OuterRef("qualification_id")).values("title")[:1]
            )
        )
    )
    assert len(qs) == 1
    assert qs[0].qualification_id == qualifications.nfs.id
    assert qs[0].qualification_title == qualifications.nfs.title


@pytest.mark.django_db
def test_confirm_qualification_granting(superuser, qualifications_consequence, qualifications):
    assert qualifications.nfs not in qualifications_consequence.user.qualifications
    qualifications_consequence.confirm(superuser)
    assert qualifications.nfs in qualifications_consequence.user.qualifications
