from datetime import date, datetime

import pytest
from django.urls import reverse

from ephios.core.models import (
    AbstractParticipation,
    LocalParticipation,
    QualificationGrant,
    Shift,
    UserProfile,
)
from ephios.plugins.basesignupflows.flow.participant import RequestConfirmSignupFlow
from ephios.plugins.complexsignup.models import (
    BlockComposition,
    BuildingBlock,
    BuildingBlockType,
    Position,
)
from ephios.plugins.complexsignup.structure import ComplexShiftStructure, iter_atomic_blocks
from ephios.plugins.complexsignup.templatetags.complex_extra import has_complex_free


@pytest.fixture
def basic_blocks(qualifications):
    rtw = BuildingBlock.objects.create(name="RTW", block_type=BuildingBlockType.ATOMIC)
    p = Position.objects.create(block=rtw)
    p.qualifications.set([qualifications.nfs])
    p = Position.objects.create(block=rtw)
    p.qualifications.set([qualifications.rs, qualifications.c1])
    c1nfs = BuildingBlock.objects.create(name="C1NFS")
    p = Position.objects.create(block=c1nfs)
    p.qualifications.set([qualifications.nfs, qualifications.c1])
    return [rtw, c1nfs]


@pytest.fixture
def composite_block(basic_blocks):
    block = BuildingBlock.objects.create(
        name="Rettungswache", block_type=BuildingBlockType.COMPOSITE
    )
    BlockComposition.objects.create(
        composite_block=block,
        sub_block=basic_blocks[0],
        label="",
    )
    BlockComposition.objects.create(
        composite_block=block,
        sub_block=basic_blocks[0],
        label="Sonderbedarf",
    )
    BlockComposition.objects.create(
        composite_block=block,
        sub_block=basic_blocks[1],
        label="Nord/10/1",
        optional=True,
    )
    return block


@pytest.fixture
def two_rtw_shift(event, basic_blocks, tz):
    return Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 7, 1, 7, 0).astimezone(tz),
        start_time=datetime(2099, 7, 1, 8, 0).astimezone(tz),
        end_time=datetime(2099, 7, 1, 20, 0).astimezone(tz),
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        signup_flow_configuration={},
        structure_slug=ComplexShiftStructure.slug,
        structure_configuration={
            "minimum_age": None,
            "signup_until": None,
            "user_can_decline_confirmed": True,
            "choose_preferred_unit": True,
            "starting_blocks": [
                {
                    "uuid": "rtw1-uuid",
                    "building_block": basic_blocks[0].pk,
                    "optional": False,
                    "label": "22-RTW-A",
                },
                {
                    "uuid": "rtw2-uuid",
                    "building_block": basic_blocks[0].pk,
                    "optional": False,
                    "label": "22-RTW-B",
                },
            ],
        },
    )


@pytest.fixture
def rtw_nfsc1_shift(event, basic_blocks, tz):
    return Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 7, 1, 7, 0).astimezone(tz),
        start_time=datetime(2099, 7, 1, 8, 0).astimezone(tz),
        end_time=datetime(2099, 7, 1, 20, 0).astimezone(tz),
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        signup_flow_configuration={},
        structure_slug=ComplexShiftStructure.slug,
        structure_configuration={
            "minimum_age": None,
            "signup_until": None,
            "user_can_decline_confirmed": True,
            "choose_preferred_unit": True,
            "starting_blocks": [
                {
                    "uuid": "rtw1-uuid",
                    "building_block": basic_blocks[0].pk,
                    "optional": False,
                    "label": "22-RTW-A",
                },
                {
                    "uuid": "nfsc1-uuid",
                    "building_block": basic_blocks[1].pk,
                    "optional": False,
                    "label": "Field supervisor",
                },
            ],
        },
    )


@pytest.fixture
def rettungswache_shift(event, composite_block, tz):
    return Shift.objects.create(
        event=event,
        meeting_time=datetime(2099, 7, 1, 7, 0).astimezone(tz),
        start_time=datetime(2099, 7, 1, 8, 0).astimezone(tz),
        end_time=datetime(2099, 7, 1, 20, 0).astimezone(tz),
        signup_flow_slug=RequestConfirmSignupFlow.slug,
        signup_flow_configuration={},
        structure_slug=ComplexShiftStructure.slug,
        structure_configuration={
            "minimum_age": None,
            "signup_until": None,
            "user_can_decline_confirmed": True,
            "choose_preferred_unit": True,
            "starting_blocks": [
                {
                    "uuid": "rettungswache-uuid",
                    "building_block": composite_block.pk,
                    "optional": False,
                    "label": "Nord",
                },
            ],
        },
    )


@pytest.fixture
def nfs_user(qualifications, tz, groups):
    managers, planners, volunteers = groups
    volunteer = UserProfile.objects.create(
        display_name="Nico Notsann",
        email="nico@localhost",
        date_of_birth=date(1985, 1, 1),
        password="dummy",
    )
    QualificationGrant.objects.create(
        user=volunteer,
        qualification=qualifications.nfs,
        expires=None,
    )
    volunteers.user_set.add(volunteer)
    return volunteer


@pytest.fixture
def rs_user(qualifications, tz, groups):
    managers, planners, volunteers = groups
    volunteer = UserProfile.objects.create(
        display_name="Rico Rettsan",
        email="rico@localhost",
        date_of_birth=date(1995, 1, 1),
        password="dummy",
    )
    QualificationGrant.objects.create(
        user=volunteer,
        qualification=qualifications.rs,
        expires=None,
    )
    QualificationGrant.objects.create(
        user=volunteer,
        qualification=qualifications.c1,
        expires=None,
    )
    volunteers.user_set.add(volunteer)
    return volunteer


@pytest.mark.parametrize(
    "participation_state,designate_rtw1,assert_rtw1_free",
    [
        (
            # empty shift
            AbstractParticipation.States.USER_DECLINED,
            False,  # designate participants to RTW 1
            True,  # expected: RTW 1 has free
        ),
        (
            # requested still considered free
            AbstractParticipation.States.REQUESTED,
            False,
            True,
        ),
        (
            # requested and designated also free
            AbstractParticipation.States.REQUESTED,
            True,
            True,
        ),
        (
            # confirmed undesignated --> can move to other RTW --> free
            AbstractParticipation.States.CONFIRMED,
            False,
            True,
        ),
        (
            # confirmed and designated --> not free
            AbstractParticipation.States.CONFIRMED,
            True,
            False,
        ),
    ],
)
def test_has_complex_free_with_alternative_unit(
    two_rtw_shift,
    nfs_user,
    rs_user,
    participation_state,
    designate_rtw1,
    assert_rtw1_free,
):
    """
    This tests the has_complex_free function in a scenario where participants also fit another unit. (two RTWs)
    """
    structure_data = {}
    if designate_rtw1:
        structure_data["dispatched_unit_path"] = "root.rtw1-uuid."

    LocalParticipation.objects.create(
        shift=two_rtw_shift,
        user=nfs_user,
        state=participation_state,
        structure_data=structure_data,
    )
    LocalParticipation.objects.create(
        shift=two_rtw_shift,
        user=rs_user,
        state=participation_state,
        structure_data=structure_data,
    )

    structure = two_rtw_shift.structure
    structure._assume_cache()
    rtw1_block, rtw2_block = list(iter_atomic_blocks(structure._structure))
    assert "rtw2-uuid" in rtw2_block["path"], "something got mixed up"
    assert has_complex_free(rtw1_block, two_rtw_shift) == assert_rtw1_free
    assert has_complex_free(rtw2_block, two_rtw_shift)


@pytest.mark.parametrize(
    "participation_state,designate_rtw1,assert_rtw1_free",
    [
        (
            # empty shift
            AbstractParticipation.States.USER_DECLINED,
            False,
            True,
        ),
        (
            # requested still considered free
            AbstractParticipation.States.REQUESTED,
            False,
            True,
        ),
        (
            # requested and designated also free
            AbstractParticipation.States.REQUESTED,
            True,
            True,
        ),
        (
            # confirmed undesignated --> cannot move to other block! --> not free
            AbstractParticipation.States.CONFIRMED,
            False,
            False,
        ),
        (
            # confirmed and designated --> also not free
            AbstractParticipation.States.CONFIRMED,
            True,
            False,
        ),
    ],
)
def test_has_complex_free_without_alternative_unit(
    rtw_nfsc1_shift,
    nfs_user,
    rs_user,
    participation_state,
    designate_rtw1,
    assert_rtw1_free,
):
    """
    This tests the has_complex_free function in a scenario where participants cannot fit another unit. (RTW and NFS+C1 combo)
    """
    structure_data = {}
    if designate_rtw1:
        structure_data["dispatched_unit_path"] = "root.rtw1-uuid."

    LocalParticipation.objects.create(
        shift=rtw_nfsc1_shift,
        user=nfs_user,
        state=participation_state,
        structure_data=structure_data,
    )
    LocalParticipation.objects.create(
        shift=rtw_nfsc1_shift,
        user=rs_user,
        state=participation_state,
        structure_data=structure_data,
    )

    structure = rtw_nfsc1_shift.structure
    structure._assume_cache()
    rtw1_block, nfsc1_block = list(iter_atomic_blocks(structure._structure))
    assert "nfsc1-uuid" in nfsc1_block["path"], "something got mixed up"
    assert has_complex_free(rtw1_block, rtw_nfsc1_shift) == assert_rtw1_free
    assert has_complex_free(nfsc1_block, rtw_nfsc1_shift)


def test_complex_renders_without_errors(two_rtw_shift, planner, django_app):
    assert (
        "22-RTW-A"
        in django_app.get(
            reverse(
                "core:event_detail",
                kwargs=dict(
                    pk=two_rtw_shift.event.pk,
                    slug="nottheactualslug",
                ),
            ),
            user=planner,
        ).follow()
    )


def test_views_with_block_missing_from_db(
    django_app, two_rtw_shift, basic_blocks, planner, nfs_user
):
    LocalParticipation.objects.create(
        shift=two_rtw_shift,
        user=nfs_user,
        state=AbstractParticipation.States.CONFIRMED,
        structure_data={"dispatched_unit_path": "root.rtw1-uuid."},
    )
    basic_blocks[0].delete()
    assert (
        "unassigned"
        in django_app.get(
            reverse(
                "core:event_detail",
                kwargs=dict(
                    pk=two_rtw_shift.event.pk,
                    slug="nottheactualslug",
                ),
            ),
            user=nfs_user,
        ).follow()
    )
    django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=two_rtw_shift.pk)), user=planner
    )
    response = django_app.get(
        reverse("core:signup_action", kwargs=dict(pk=two_rtw_shift.pk)), user=nfs_user
    )
    response.form.submit(name="signup_choice", value="sign_up")


def test_complex_composite_signup_disposition_and_export(
    django_app, rettungswache_shift, nfs_user, planner, composite_block
):
    assert composite_block.is_composite()
    signup_form = django_app.get(
        reverse("core:signup_action", kwargs=dict(pk=rettungswache_shift.pk)), user=nfs_user
    ).form
    signup_form["preferred_unit_path"] = "root.rettungswache-uuid.1."
    response = signup_form.submit(name="signup_choice", value="sign_up").follow()
    assert str(nfs_user) in response
    assert (
        LocalParticipation.objects.get(shift=rettungswache_shift, user=nfs_user).state
        == AbstractParticipation.States.REQUESTED
    )

    disposition_form = django_app.get(
        reverse("core:shift_disposition", kwargs=dict(pk=rettungswache_shift.pk)), user=planner
    ).forms["participations-form"]
    disposition_form["participations-0-unit_path"] = "root.rettungswache-uuid.2."
    disposition_form["participations-0-state"] = AbstractParticipation.States.CONFIRMED
    disposition_form.submit()
    assert django_app.get(
        reverse("core:event_detail_pdf", kwargs=dict(pk=rettungswache_shift.event.pk)), user=planner
    )
