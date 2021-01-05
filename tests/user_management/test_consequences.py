from datetime import datetime

import pytest
from django.db.models import F, OuterRef, Prefetch, Subquery

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
def test_prefetch_with_json(qualifications_consequence, qualifications):
    qs = Consequence.objects.filter(state=Consequence.States.NEEDS_CONFIRMATION).prefetch_related(
        Prefetch(
            "data__qualification_id", queryset=Qualification.objects.all(), to_attr="qualification"
        )
    )
    assert len(qs) == 1
    # assert qs[0].qualification == qualifications.nfs

    ##########################

    qs = (
        Consequence.objects.filter(state=Consequence.States.NEEDS_CONFIRMATION)
        .annotate(qualification_id=F("data__qualification_id"))
        .annotate(
            qualification_title=Subquery(
                Qualification.objects.filter(pk=OuterRef("qualification_id")).values("title")[:1]
            )
        )
    )
    assert len(qs) == 1
    assert qs[0].qualification_id == qualifications.nfs.id


@pytest.mark.django_db
def test_confirm_qualification_granting(superuser, qualifications_consequence, qualifications):
    assert qualifications.nfs not in qualifications_consequence.user.qualifications
    qualifications_consequence.confirm(superuser)
    assert qualifications.nfs in qualifications_consequence.user.qualifications
