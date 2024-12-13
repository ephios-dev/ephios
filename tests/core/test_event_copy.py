from datetime import datetime, time, timedelta

import recurrence
from django.urls import reverse
from django.utils import timezone
from guardian.shortcuts import assign_perm

from ephios.core.models import Event, Shift
from ephios.extra.permissions import get_groups_with_perms


class TestEventCopy:
    def assert_dates(self, event, occurrences, volunteers, planners):
        for shift_date in occurrences:
            shift = Shift.objects.get(start_time__date=shift_date)
            assert shift.event.title == event.title
            assert shift.event.get_start_time() == shift.start_time
            assert shift.meeting_time.date() == shift.start_time.date()
            assert shift.end_time.date() == shift.start_time.date()
            assert (volunteers and planners) in get_groups_with_perms(
                shift.event, only_with_perms_in=["view_event"]
            )
            assert planners in get_groups_with_perms(
                shift.event, only_with_perms_in=["change_event"]
            )

    def test_event_copy_by_rule(self, django_app, planner, event, groups):
        managers, planners, volunteers = groups
        response = django_app.get(reverse("core:event_copy", kwargs={"pk": event.id}), user=planner)
        event_count = Event.objects.all().count()
        form = response.form
        recurr = recurrence.Recurrence(
            dtstart=datetime.now(),
            rrules=[
                recurrence.Rule(freq=recurrence.WEEKLY, count=3, byday=datetime.now().weekday())
            ],
        )
        form["recurrence"] = str(recurr)
        form.submit()
        occurrences = recurr.between(
            datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=365)
        )
        assert Event.objects.all().count() == event_count + 3
        assert Shift.objects.filter(start_time__date__in=occurrences).count() == 3
        self.assert_dates(event, occurrences, volunteers, planners)

    def test_event_copy_by_date(self, django_app, planner, event, groups, volunteer):
        managers, planners, volunteers = groups
        assign_perm(
            "change_event", volunteer, event
        )  # test that single user permissions are transferred
        response = django_app.get(reverse("core:event_copy", kwargs={"pk": event.id}), user=planner)
        event_count = Event.objects.all().count()
        form = response.form
        target_date = datetime.now() + timedelta(days=14)
        recurr = recurrence.Recurrence(
            dtstart=datetime.now(),
            rdates=[target_date],
            include_dtstart=False,
        )
        form["recurrence"] = str(recurr)
        form.submit()
        occurrences = recurr.between(
            datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=365)
        )
        new_event = Event.objects.get(title=event.title, shifts__start_time__date=target_date)
        assert Event.objects.all().count() == event_count + 1
        assert Shift.objects.filter(start_time__date__in=occurrences).count() == 1
        self.assert_dates(event, occurrences, volunteers, planners)
        assert planner.has_perm("change_event", new_event)
        assert set(get_groups_with_perms(new_event, only_with_perms_in=["change_event"])) == set(
            get_groups_with_perms(event, only_with_perms_in=["change_event"])
        )

    def test_event_multi_shift_copy(self, django_app, planner, groups, multi_shift_event):
        managers, planners, volunteers = groups
        response = django_app.get(
            reverse("core:event_copy", kwargs={"pk": multi_shift_event.id}),
            user=planner,
        )
        event_count = Event.objects.all().count()
        form = response.form
        recurr = recurrence.Recurrence(
            dtstart=datetime.now(),
            rrules=[
                recurrence.Rule(freq=recurrence.WEEKLY, count=3, byday=datetime.now().weekday())
            ],
        )
        form["recurrence"] = str(recurr)
        form.submit()
        occurrences = recurr.between(
            datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=365)
        )
        assert Event.objects.all().count() == event_count + 3
        assert Shift.objects.filter(start_time__date__in=occurrences).count() == 3
        for shift_date in occurrences:
            shift = Shift.objects.get(start_time__date=shift_date)
            assert shift.event.title == multi_shift_event.title
            assert shift.event.get_start_time() == shift.start_time
            assert shift.meeting_time.date() == shift.start_time.date()
            assert shift.end_time.date() in [
                shift.start_time.date(),
                shift.start_time.date() + timedelta(days=1),
            ]
            assert (volunteers and planners) in get_groups_with_perms(
                shift.event, only_with_perms_in=["view_event"]
            )
            assert planners in get_groups_with_perms(
                shift.event, only_with_perms_in=["change_event"]
            )
            second_shift = shift.event.shifts.get(start_time__date=shift_date + timedelta(days=1))
            assert second_shift.start_time.date() == shift.start_time.date() + timedelta(days=1)

    def test_event_to_next_day_copy(self, django_app, planner, event_to_next_day, groups):
        managers, planners, volunteers = groups
        response = django_app.get(
            reverse("core:event_copy", kwargs={"pk": event_to_next_day.id}),
            user=planner,
        )
        event_count = Event.objects.all().count()
        form = response.form
        target_date = datetime.now() + timedelta(days=14)
        recurr = recurrence.Recurrence(
            dtstart=datetime.now(), rdates=[target_date], include_dtstart=False
        )
        form["recurrence"] = str(recurr)
        form.submit()
        occurrences = recurr.between(
            datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=365)
        )
        assert Event.objects.all().count() == event_count + 1
        assert Shift.objects.filter(start_time__date__in=occurrences).count() == 1
        for shift_date in occurrences:
            shift = Shift.objects.get(start_time__date=shift_date)
            assert shift.event.title == event_to_next_day.title
            assert shift.event.get_start_time() == shift.start_time
            assert shift.meeting_time.date() == shift.start_time.date()
            assert shift.end_time.date() == shift.start_time.date() + timedelta(days=1)
            assert (volunteers and planners) in get_groups_with_perms(
                shift.event, only_with_perms_in=["view_event"]
            )
            assert planners in get_groups_with_perms(
                shift.event, only_with_perms_in=["change_event"]
            )

    def test_copy_overnight_event_with_times_close_to_midnight(
        self, django_app, planner, event, tz
    ):
        original_shift = event.shifts.first()
        original_shift.start_time = datetime.combine(
            original_shift.start_time.date(), time(hour=23, minute=30), tzinfo=tz
        )
        original_shift.end_time = datetime.combine(
            original_shift.start_time.date() + timedelta(days=1), time(hour=0, minute=30), tzinfo=tz
        )
        original_shift.save()
        response = django_app.get(reverse("core:event_copy", kwargs={"pk": event.id}), user=planner)
        form = response.form
        target_starttime = timezone.now() + timedelta(days=14)
        recurr = recurrence.Recurrence(
            dtstart=target_starttime,
            rdates=[target_starttime],
        )
        form["recurrence"] = str(recurr)
        form.submit()
        copied_shift = Shift.objects.exclude(event=event).get()
        assert copied_shift.start_time.astimezone(tz).date() == target_starttime.date()
        assert copied_shift.start_time.astimezone(tz).time() == original_shift.start_time.time()
        assert (
            copied_shift.end_time.astimezone(tz).date()
            == (target_starttime + timedelta(days=1)).date()
        )
        assert copied_shift.end_time.astimezone(tz).time() == original_shift.end_time.time()
