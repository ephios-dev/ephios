import pytest

from ephios.core.forms.users import MANAGEMENT_PERMISSIONS
from ephios.extra.permissions import get_groups_with_perms


def test_querying_get_groups_with_perms(groups, event):
    managers, planners, volunteers = groups

    groups_with_any_perm = get_groups_with_perms(
        event,
        only_with_perms_in=["view_event", "change_event"],
        must_have_all_perms=False,
    )
    assert set(groups) == set(groups_with_any_perm)

    groups_with_all_perms = get_groups_with_perms(
        event, only_with_perms_in=["view_event", "change_event"], must_have_all_perms=True
    )
    assert set(groups_with_all_perms) == {managers, planners}

    management_groups_by_list = get_groups_with_perms(
        only_with_perms_in=MANAGEMENT_PERMISSIONS,
        must_have_all_perms=True,
    )
    assert set(management_groups_by_list) == {managers}

    management_groups_by_list = get_groups_with_perms(
        only_with_perms_in=["core.view_event", "core.change_event"],
        must_have_all_perms=False,
    )
    assert set(management_groups_by_list) == {managers}

    with pytest.raises(ValueError):
        # view_event is not a specific enough to identify a permission
        get_groups_with_perms(
            only_with_perms_in=["view_event"],
        )
