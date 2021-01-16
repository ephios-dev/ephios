from datetime import datetime

import pytest
from django.db.models import OuterRef, Subquery
from django.db.models.fields.json import KeyTransform
from django.urls import reverse

from ephios.user_management.consequences import QualificationConsequenceHandler
from ephios.user_management.models import Consequence, Qualification


@pytest.mark.django_db
class TestQualificationConsequence:
    def test_render_qualification_granting(self, qualifications_consequence):
        assert qualifications_consequence.render()

    def test_render_qualification_without_shift_information(self, volunteer, qualifications, tz):
        c = QualificationConsequenceHandler.create(
            user=volunteer,
            qualification=qualifications.nfs,
            expires=datetime(2064, 4, 1).astimezone(tz),
        )
        assert c.render()

    def test_annotation_with_json(self, qualifications_consequence, qualifications):
        qs = (
            Consequence.objects.filter(state=Consequence.States.NEEDS_CONFIRMATION)
            .annotate(qualification_id=KeyTransform("qualification_id", "data"))
            .annotate(
                qualification_title=Subquery(
                    Qualification.objects.filter(pk=OuterRef("qualification_id")).values("title")[
                        :1
                    ]
                )
            )
        )
        assert len(qs) == 1
        assert qs[0].qualification_id == qualifications.nfs.id
        assert qs[0].qualification_title == qualifications.nfs.title

    def test_confirm_qualification_granting(
        self, superuser, qualifications_consequence, qualifications
    ):
        assert qualifications.nfs not in qualifications_consequence.user.qualifications
        qualifications_consequence.confirm(superuser)
        assert qualifications.nfs in qualifications_consequence.user.qualifications

    def test_extend_qualification(
        self, django_app, qualified_volunteer, qualifications_consequence, qualifications
    ):
        with pytest.raises(Qualification.DoesNotExist):
            qualified_volunteer.qualifications.get(
                pk=qualifications.nfs.pk, expires=qualifications_consequence.data.get("expires")
            )
        qualifications_consequence.confirm(qualified_volunteer)
        assert qualified_volunteer.qualifications.get(
            pk=qualifications.nfs.pk, expires=qualifications_consequence.data.get("expires")
        )


@pytest.mark.django_db
class TestWorkingHourConsequence:
    def test_request_workinghour(self, django_app, volunteer):
        form = django_app.get(reverse("user_management:request_workinghour"), user=volunteer).form
        form["when"] = datetime.now().date()
        form["hours"] = 42
        form["reason"] = "testing"
        form.submit()
        Consequence.objects.get(
            user=volunteer, data__date=datetime.now().date(), data__hours=42, data__reason="testing"
        )

    def test_render_workinghour_consequence(self, workinghours_consequence):
        assert workinghours_consequence.render()

    def test_confirm_workinghours(self, volunteer, superuser, workinghours_consequence):
        assert volunteer.get_workhour_items()[0] == 0
        workinghours_consequence.confirm(superuser)
        assert volunteer.get_workhour_items()[0] == workinghours_consequence.data.get("hours")


@pytest.mark.django_db
def test_post_consequence_confirm(csrf_exempt_django_app, superuser, qualifications_consequence):
    assert qualifications_consequence.state == Consequence.States.NEEDS_CONFIRMATION
    POST_DATA = {"action": "confirm"}
    csrf_exempt_django_app.post(
        reverse("user_management:consequence_edit", kwargs=dict(pk=qualifications_consequence.pk)),
        user=superuser,
        params=POST_DATA,
    )
    qualifications_consequence.refresh_from_db()
    assert qualifications_consequence.state == Consequence.States.EXECUTED


@pytest.mark.django_db
def test_post_consequence_deny(csrf_exempt_django_app, superuser, qualifications_consequence):
    assert qualifications_consequence.state == Consequence.States.NEEDS_CONFIRMATION
    POST_DATA = {"action": "deny"}
    csrf_exempt_django_app.post(
        reverse("user_management:consequence_edit", kwargs=dict(pk=qualifications_consequence.pk)),
        user=superuser,
        params=POST_DATA,
    )
    qualifications_consequence.refresh_from_db()
    assert qualifications_consequence.state == Consequence.States.DENIED
