import re
from collections import OrderedDict
from datetime import date, datetime
from unittest import mock

import pytest
from django import forms
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.timezone import make_aware
from guardian.shortcuts import assign_perm, remove_perm

from ephios.core.forms.users import HR_PERMISSIONS, MANAGEMENT_PERMISSIONS
from ephios.core.models import Notification, Qualification, UserProfile
from ephios.core.services.notifications.types import NewProfileNotification
from ephios.core.views.accounts import UserProfileFilterForm


class TestUserProfileView:
    def test_correct_user_data_displayed(
        self, django_app, superuser, manager, planner, volunteer, responsible_user
    ):
        users = [superuser, manager, planner, volunteer, responsible_user]
        for user in users:
            response = django_app.get(reverse("core:settings_personal_data"), user=user)
            assert response.html.find("dd", string=user.display_name)
            assert response.html.find("dd", string=user.email)
            assert response.html.find(
                "dd", string=date_format(user.date_of_birth, format="DATE_FORMAT")
            )
            assert response.html.find("dd", string=user.phone)

    def test_correct_qualifications(self, django_app, qualified_volunteer):
        response = django_app.get(reverse("core:settings_personal_data"), user=qualified_volunteer)
        for q in qualified_volunteer.qualifications:
            assert q.expires is None or response.html.find_all(
                "li", string=re.compile(f"{q.title}")
            )

    def test_userprofile_list_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("core:userprofile_list"), user=volunteer, status=403)
        assert response.status_code == 403

    def test_userprofile_list(self, django_app, superuser):
        response = django_app.get(reverse("core:userprofile_list"), user=superuser)
        assert response.status_code == 200
        assert all(
            email in response.text
            for email in UserProfile.objects.all().values_list("email", flat=True)
        )
        edit_links = [
            reverse("core:userprofile_edit", kwargs={"pk": userprofile_id})
            for userprofile_id in UserProfile.objects.all().values_list("id", flat=True)
        ]
        assert response.html.find_all("a", href=edit_links)

    @pytest.fixture()
    def userprofile_list_filter_form(self, django_app, superuser, groups):
        # patch UserProfileFilterForm qualification widget to be a plain django select widget
        # so that we can easily check the rendered options

        class MockedUserProfileFilterForm(UserProfileFilterForm):
            qualification = forms.ModelChoiceField(
                queryset=Qualification.objects.all(),
                required=False,
            )

        with mock.patch(
            "ephios.core.views.accounts.UserProfileFilterForm", MockedUserProfileFilterForm
        ):
            yield django_app.get(reverse("core:userprofile_list"), user=superuser, status=200).form

    @pytest.mark.parametrize(
        "filter_group,filter_qualification,query,expected",
        [
            (
                None,
                None,
                "",
                [
                    "rica@localhost",
                    "marie@localhost",
                    "luisa@localhost",
                    "heinrich@localhost",
                    "marianne@localhost",
                ],
            ),
            (
                "Managers",
                None,
                "rica",
                ["rica@localhost"],
            ),
            (
                "Planners",
                "Notfallsanitäter",
                "",
                [],
            ),
            (
                "Volunteers",
                "Notfallsanitäter",
                "",
                ["marianne@localhost"],
            ),
            (
                None,
                None,
                "",
                [
                    "rica@localhost",
                    "marie@localhost",
                    "luisa@localhost",
                    "heinrich@localhost",
                    "marianne@localhost",
                ],
            ),
            (None, "Rettungssanitäter", "", ["marianne@localhost"]),
            (None, "Notarzt", "", []),
        ],
    )
    def test_userprofile_list_filter_select(
        self, userprofile_list_filter_form, filter_group, filter_qualification, query, expected
    ):
        if filter_group:
            userprofile_list_filter_form["group"].select(text=filter_group)
        if filter_qualification:
            userprofile_list_filter_form["qualification"].select(text=filter_qualification)
        userprofile_list_filter_form["query"] = query
        response = userprofile_list_filter_form.submit()
        assert all(email in response.text for email in expected)
        assert not any(
            email in response.text
            for email in UserProfile.objects.exclude(email__in=expected).values_list(
                "email", flat=True
            )
        )

    def test_userprofile_create_permission_required(self, django_app, volunteer):
        response = django_app.get(reverse("core:userprofile_create"), user=volunteer, status=403)
        assert response.status_code == 403

    def test_userprofile_create(self, csrf_exempt_django_app, groups, manager, qualifications):
        managers, planners, volunteers = groups
        response = csrf_exempt_django_app.get(reverse("core:userprofile_create"), user=manager)
        assert response.status_code == 200
        userprofile_email = "testuser@localhost"

        POST_DATA = OrderedDict({
            "email": userprofile_email,
            "display_name": "testname",
            "date_of_birth": "1999-01-01",
            "phone": "",
            "groups": volunteers.id,
            "is_active": "on",
            "qualification_grants": "",
            "qualification_grants-0-qualification": qualifications.rs.id,
            "qualification_grants-0-expires": "",
            "qualification_grants-1-qualification": qualifications.na.id,
            "qualification_grants-1-expires": "2030-01-01",
            "qualification_grants-INITIAL_FORMS": "0",
            "qualification_grants-MAX_NUM_FORMS": "1000",
            "qualification_grants-MIN_NUM_FORMS": "0",
            "qualification_grants-TOTAL_FORMS": "2",
        })
        response = csrf_exempt_django_app.post(
            reverse("core:userprofile_create"),
            user=manager,
            params=POST_DATA,
        )

        assert response.status_code == 302
        userprofile = UserProfile.objects.get(email=userprofile_email)
        assert userprofile.email == userprofile_email
        assert Notification.objects.count() == 1
        assert Notification.objects.first().slug == NewProfileNotification.slug

        assert userprofile.display_name == "testname"
        assert userprofile.date_of_birth == date(1999, 1, 1)
        assert not userprofile.phone
        assert userprofile.is_active
        assert set(userprofile.groups.all()) == {volunteers}
        assert set(userprofile.qualifications) == {qualifications.rs, qualifications.na}
        assert userprofile.qualifications.get(id=qualifications.rs.id).expires is None
        assert userprofile.qualifications.get(id=qualifications.na.id).expires == make_aware(
            datetime.max.replace(2030, 1, 1)
        )

    def test_hr_user_can_create_user(self, django_app, groups, manager, qualifications):
        managers, planners, volunteers = groups

        # demote managers to HR
        for permission in set(MANAGEMENT_PERMISSIONS) - set(HR_PERMISSIONS):
            remove_perm(permission, managers)

        form = django_app.get(reverse("core:userprofile_create"), user=manager).form
        form["email"] = "testuser@localhost"
        form["display_name"] = "testname"
        form["date_of_birth"] = "1999-01-01"
        assert form.submit().follow()

    def test_userprofile_edit(self, django_app, groups, manager, volunteer):
        userprofile = volunteer
        managers, planners, volunteers = groups
        response = django_app.get(
            reverse("core:userprofile_edit", kwargs={"pk": userprofile.id}), user=manager
        )
        form = response.form
        userprofile_email = "newmail@localhost"
        userprofile_phone = "12345"
        form["email"] = userprofile_email
        form["phone"] = userprofile_phone
        form["groups"].select_multiple(texts=["Volunteers", "Planners"])
        response = form.submit()
        assert response.status_code == 302
        userprofile.refresh_from_db()
        assert userprofile.email == userprofile_email
        assert set(userprofile.groups.all()) == {volunteers, planners}

    def test_userprofile_delete(self, django_app, groups, volunteer, manager):
        userprofile = volunteer
        response = django_app.get(
            reverse("core:userprofile_delete", kwargs={"pk": userprofile.id}),
            user=manager,
        )
        assert response.status_code == 200
        response = response.form.submit()
        assert response.status_code == 302
        with pytest.raises(UserProfile.DoesNotExist):
            UserProfile.objects.get(email=userprofile.email).exists()

    def test_userprofile_password_reset(self, django_app, groups, volunteer, manager):
        userprofile = volunteer
        response = django_app.get(
            reverse("core:userprofile_password_reset", kwargs={"pk": userprofile.id}),
            user=manager,
        )
        assert response.status_code == 200
        response.form.submit()
        assert response.status_code == 200

    def test_userprofile_group_membership_edit_by_hr_allowed(
        self, django_app, volunteer, hr_group, groups
    ):
        managers, planners, volunteers = groups
        form = django_app.get(
            reverse("core:userprofile_edit", kwargs={"pk": volunteer.id}), user=volunteer
        ).form
        form["groups"].force_value([volunteers.id])
        response = form.submit()
        assert response.status_code == 302
        assert set(volunteer.groups.all()) == {volunteers}

    def test_userprofile_group_membership_edit_by_hr_forbidden(
        self, django_app, volunteer, hr_group, groups
    ):
        managers, planners, volunteers = groups
        assert set(volunteer.groups.all()) == {hr_group, volunteers}
        form = django_app.get(
            reverse("core:userprofile_edit", kwargs={"pk": volunteer.id}), user=volunteer
        ).form
        form["groups"].force_value([managers.id])
        response = form.submit()
        assert response.status_code == 200
        assert set(volunteer.groups.all()) == {hr_group, volunteers}

    def test_is_staff_flag_cannot_be_changed_by_non_staff_user(
        self, django_app, volunteer, manager, groups
    ):
        form = django_app.get(
            reverse("core:userprofile_edit", kwargs={"pk": volunteer.id}), user=manager
        ).form
        form["is_staff"] = True
        form.submit()
        assert not manager.is_staff
        assert not UserProfile.objects.get(id=volunteer.id).is_staff

    def test_staffuser_can_change_is_staff_flag(self, django_app, volunteer, superuser, groups):
        form = django_app.get(
            reverse("core:userprofile_edit", kwargs={"pk": volunteer.id}), user=superuser
        ).form
        form["is_staff"] = True
        form.submit()
        assert UserProfile.objects.get(id=volunteer.id).is_staff

    def test_staff_flag_cannot_be_removed_from_last_staff_user(self, django_app, superuser):
        form = django_app.get(
            reverse("core:userprofile_edit", kwargs={"pk": superuser.id}), user=superuser
        ).form
        form["is_staff"] = False
        response = form.submit()
        assert response.status_code == 200
        assert "least one user must be technical administrator" in response.text
        assert UserProfile.objects.get(id=superuser.id).is_staff

    def test_last_staff_user_cannot_be_deleted(self, django_app, groups, manager, superuser):
        response = django_app.get(
            reverse("core:userprofile_delete", kwargs={"pk": superuser.id}),
            user=manager,
        )
        response = response.form.submit()
        assert response.status_code == 200
        assert "least one user must be technical administrator" in response.text
        assert UserProfile.objects.get(id=superuser.id).is_staff

    def test_email_cannot_be_changed_if_user_is_in_more_groups(
        self, django_app, groups, planner, manager
    ):
        managers, planners, volunteers = groups
        # promote planners to user management
        assign_perm("core.change_userprofile", planners)

        form = django_app.get(
            reverse("core:userprofile_edit", kwargs={"pk": manager.id}),
            user=planner,
        ).form

        assert "disabled" in form.fields["email"][0].attrs
