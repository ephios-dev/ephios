from collections import OrderedDict
from datetime import datetime

import pytest
from django.urls import reverse

from ephios.core.models import AbstractParticipation, LocalParticipation, Shift
from ephios.plugins.basesignup.signup.section_based import SectionBasedSignupMethod

KTW_UUID = "f92fe836-6dc5-4afd-b488-aee3fe7eda32"


@pytest.fixture
def sectioned_shift(event, tz, qualifications):
    return Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 7, 1, 7, 0).astimezone(tz),
        start_time=datetime(2099, 7, 1, 8, 0).astimezone(tz),
        end_time=datetime(2099, 7, 1, 20, 0).astimezone(tz),
        signup_method_slug=SectionBasedSignupMethod.slug,
        signup_configuration={
            "minimum_age": None,
            "signup_until": None,
            "user_can_decline_confirmed": False,
            "choose_preferred_section": True,
            "sections": [
                {
                    "title": "KTW",
                    "qualifications": [qualifications.b, qualifications.rs],
                    "min_count": 2,
                    "uuid": KTW_UUID,
                },
                {
                    "title": "ITS",
                    "qualifications": [qualifications.na],
                    "min_count": 1,
                    "uuid": "e2df480f-1f11-442c-be11-3cccf7e6ea19",
                },
            ],
        },
    )


@pytest.mark.django_db
@pytest.mark.ignore_template_errors  # shift_form uses unbound object to look special for creation
def test_configuration(csrf_exempt_django_app, planner, event, qualifications):
    POST_DATA = OrderedDict(
        {
            "choose_preferred_section": "on",
            "date": "2023-06-30",
            "end_time": "01:00:00",
            "meeting_time": "15:30:00",
            "minimum_age": "",
            "sections": "",
            "sections-0-min_count": "2",
            "sections-0-qualifications": str(qualifications.rs.id),
            "sections-0-title": "KTW 10-85-1",
            "sections-0-uuid": "",
            "sections-1-min_count": "2",
            "sections-1-qualifications": str(qualifications.na.id),
            "sections-1-title": "ITS",
            "sections-1-uuid": "",
            "sections-INITIAL_FORMS": "2",
            "sections-MAX_NUM_FORMS": "1000",
            "sections-MIN_NUM_FORMS": "1",
            "sections-TOTAL_FORMS": "2",
            "signup_method_slug": "section_based",
            "signup_until_0": "",
            "signup_until_1": "",
            "start_time": "16:00:00",
        }
    )

    csrf_exempt_django_app.get(
        reverse("core:event_createshift", kwargs=dict(pk=event.pk)),
        user=planner,
    )
    # no csrf check for plain post
    csrf_exempt_django_app.post(
        reverse("core:event_createshift", kwargs=dict(pk=event.pk)),
        user=planner,
        params=POST_DATA,
    ).follow()
    _, shift = event.shifts.order_by("id")
    assert shift.signup_method_slug == SectionBasedSignupMethod.slug
    assert len(shift.signup_method.configuration.sections) == 2


@pytest.mark.django_db
def test_signup_flow(django_app, qualified_volunteer, planner, event, sectioned_shift):
    # request a participation as volunteer on *second* shift
    response = (
        django_app.get(
            reverse("core:event_detail", kwargs=dict(pk=event.pk)),
            user=qualified_volunteer,
        )
        .forms[1]
        .submit(name="signup_choice", value="sign_up")
        .follow()
    )
    response.form["section"] = KTW_UUID
    response.form.submit()
    assert (
        LocalParticipation.objects.get(user=qualified_volunteer, shift=sectioned_shift).state
        == AbstractParticipation.States.REQUESTED
    )

    # test we can't signup again
    assert (
        "You can not sign up for this shift."
        in django_app.get(
            reverse("core:event_detail", kwargs=dict(pk=event.pk)),
            user=qualified_volunteer,
        )
        .forms[1]
        .submit(name="signup_choice", value="sign_up")
        .follow()
    )

    # confirm the participation as planner
    response = django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=sectioned_shift.pk)),
        user=planner,
    )
    form = response.forms["participations-form"]
    form["participations-0-state"] = AbstractParticipation.States.CONFIRMED.value
    form.submit()
    participation = LocalParticipation.objects.get(user=qualified_volunteer, shift=sectioned_shift)
    assert participation.state == AbstractParticipation.States.CONFIRMED
    assert participation.data.get("preferred_section_uuid") == KTW_UUID
    assert participation.data.get("dispatched_section_uuid") == KTW_UUID
