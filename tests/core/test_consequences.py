import datetime

import pytest
from django.db.models import IntegerField, OuterRef, Subquery
from django.db.models.fields.json import KeyTransform
from django.db.models.functions import Cast
from django.urls import reverse

from ephios.core.consequences import (
    QualificationConsequenceHandler,
    editable_consequences,
    pending_consequences,
)
from ephios.core.models import Qualification
from ephios.core.models.users import LocalConsequence, AbstractConsequence


class TestQualificationConsequence:
    def test_render_qualification_granting(self, qualifications_consequence):
        assert qualifications_consequence.render()

    def test_render_qualification_without_shift_information(self, volunteer, qualifications, tz):
        c = QualificationConsequenceHandler.create(
            participant=volunteer.as_participant(),
            qualification=qualifications.nfs,
            expires=datetime.datetime(2064, 4, 1).astimezone(tz),
        )
        assert c.render()

    def test_annotation_with_json(self, qualifications_consequence, qualifications):
        qs = (
            LocalConsequence.objects.filter(state=LocalConsequence.States.NEEDS_CONFIRMATION)
            .annotate(
                qualification_id=Cast(KeyTransform("qualification_id", "data"), IntegerField())
            )
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
        qualifications_consequence.confirm()
        assert qualifications.nfs in qualifications_consequence.user.qualifications

    def test_extend_qualification(
        self, django_app, qualified_volunteer, qualifications_consequence, qualifications
    ):
        qualifications_consequence.user = qualified_volunteer
        qualifications_consequence.save()
        with pytest.raises(Qualification.DoesNotExist):
            qualified_volunteer.qualifications.get(
                pk=qualifications.nfs.pk, expires=qualifications_consequence.data.get("expires")
            )
        qualifications_consequence.confirm()
        assert qualified_volunteer.qualifications.get(
            pk=qualifications.nfs.pk, expires=qualifications_consequence.data.get("expires")
        )

    def test_consequence_to_decide_appears(self, groups, manager, qualifications_consequence):
        assert qualifications_consequence in editable_consequences(manager)

    def test_consequence_pends_for_user(self, volunteer, qualifications_consequence):
        assert qualifications_consequence in pending_consequences(volunteer)

    def test_render_with_deleted_event(self, volunteer, qualifications_consequence, event):
        event.delete()
        assert "after participating in deleted event" in qualifications_consequence.render()


class TestWorkingHourConsequence:
    def test_request_workinghour(self, django_app, volunteer):
        form = django_app.get(reverse("core:workinghours_request"), user=volunteer).form
        form["date"] = datetime.datetime.now().date()
        form["hours"] = 42
        form["reason"] = "testing"
        form.submit()
        LocalConsequence.objects.get(
            user=volunteer,
            data__date=datetime.datetime.now().date(),
            data__hours=42,
            data__reason="testing",
        )

    def test_render_workinghours_consequence(self, workinghours_consequence):
        assert workinghours_consequence.render()

    def test_confirm_workinghours(self, volunteer, superuser, workinghours_consequence):
        assert volunteer.get_workhour_items()[0] == datetime.timedelta(0)
        workinghours_consequence.confirm()
        assert volunteer.get_workhour_items()[0] == datetime.timedelta(
            hours=workinghours_consequence.data.get("hours")
        )

    def test_consequence_to_decide_appears(self, groups, manager, workinghours_consequence):
        assert workinghours_consequence in editable_consequences(manager)

    def test_consequence_pends_for_user(self, volunteer, workinghours_consequence):
        assert workinghours_consequence in pending_consequences(volunteer)


def test_post_consequence_confirm(csrf_exempt_django_app, superuser, qualifications_consequence):
    assert qualifications_consequence.state == LocalConsequence.States.NEEDS_CONFIRMATION
    POST_DATA = {"action": "confirm"}
    csrf_exempt_django_app.post(
        reverse("core:consequence_edit", kwargs=dict(pk=qualifications_consequence.pk)),
        user=superuser,
        params=POST_DATA,
    )
    qualifications_consequence.refresh_from_db()
    assert qualifications_consequence.state == LocalConsequence.States.EXECUTED


def test_post_consequence_deny(csrf_exempt_django_app, superuser, qualifications_consequence):
    assert qualifications_consequence.state == LocalConsequence.States.NEEDS_CONFIRMATION
    POST_DATA = {"action": "deny"}
    csrf_exempt_django_app.post(
        reverse("core:consequence_edit", kwargs=dict(pk=qualifications_consequence.pk)),
        user=superuser,
        params=POST_DATA,
    )
    qualifications_consequence.refresh_from_db()
    assert qualifications_consequence.state == LocalConsequence.States.DENIED
