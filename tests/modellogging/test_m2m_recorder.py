from django.contrib.auth import get_user_model


def test_object_create_with_m2m_added_records_related_current(superuser, manager, groups):
    user = get_user_model().objects.create(
        display_name="Linda Lessifair",
        email="linda@localhost",
        password="dummy",
    )
    user.groups.add(*groups)
    assert len(user._current_logentry.data["m2m-groups"]["data"]["current"]) == 3
