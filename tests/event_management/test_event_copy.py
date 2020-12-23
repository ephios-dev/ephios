from datetime import date, datetime, timedelta

import pytest
import recurrence
from django.urls import reverse

from ephios.event_management.models import Event, Shift
from ephios.extra.permissions import get_groups_with_perms


@pytest.mark.django_db
class TestEventCopy:
    def assert_dates(self, event, occurrences, volunteers, planners):
        for shift_date in occurrences:
            shift = Shift.objects.get(start_time__date=shift_date)
            assert shift.event.title == event.title
            assert shift.event.get_start_time() == shift.start_time
            assert shift.meeting_time.date() == shift.start_time.date()
            assert shift.end_time.date() == shift.start_time.date()
            assert (volunteers and planners) in get_groups_with_perms(shift.event, ["view_event"])
            assert planners in get_groups_with_perms(shift.event, ["change_event"])

    def test_event_copy_by_rule(self, django_app, planner, event, groups):
        managers, planners, volunteers = groups
        response = django_app.get(
            reverse("event_management:event_copy", kwargs={"pk": event.id}), user=planner
        )
        event_count = Event.objects.all().count()
        form = response.form
        recurr = recurrence.Recurrence(
            dtstart=datetime.now(),
            rrules=[
                recurrence.Rule(freq=recurrence.WEEKLY, count=3, byday=datetime.now().weekday())
            ],
        )
        form["start_date"] = datetime.now().date()
        form["recurrence"] = str(recurr)
        form.submit()
        occurrences = recurr.between(
            datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=365)
        )
        assert Event.objects.all().count() == event_count + 3
        assert Shift.objects.filter(start_time__date__in=occurrences).count() == 3
        self.assert_dates(event, occurrences, volunteers, planners)

    def test_event_copy_by_date(self, django_app, planner, event, groups):
        managers, planners, volunteers = groups
        response = django_app.get(
            reverse("event_management:event_copy", kwargs={"pk": event.id}), user=planner
        )
        event_count = Event.objects.all().count()
        form = response.form
        target_date = datetime.now() + timedelta(days=14)
        recurr = recurrence.Recurrence(
            dtstart=datetime.now(),
            rdates=[target_date],
        )
        form["start_date"] = datetime.now().date()
        form["recurrence"] = str(recurr)
        form.submit()
        occurrences = recurr.between(
            datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=365)
        )
        assert Event.objects.all().count() == event_count + 2
        assert Shift.objects.filter(start_time__date__in=occurrences).count() == 2
        self.assert_dates(event, occurrences, volunteers, planners)

    def test_event_multi_shift_copy(self, django_app, planner, groups, multi_shift_event):
        managers, planners, volunteers = groups
        response = django_app.get(
            reverse("event_management:event_copy", kwargs={"pk": multi_shift_event.id}),
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
        form["start_date"] = datetime.now().date()
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
            assert (volunteers and planners) in get_groups_with_perms(shift.event, ["view_event"])
            assert planners in get_groups_with_perms(shift.event, ["change_event"])
            second_shift = shift.event.shifts.get(start_time__date=shift_date + timedelta(days=1))
            assert second_shift.start_time.date() == shift.start_time.date() + timedelta(days=1)

    def test_event_to_next_day_copy(self, django_app, planner, event_to_next_day, groups):
        managers, planners, volunteers = groups
        response = django_app.get(
            reverse("event_management:event_copy", kwargs={"pk": event_to_next_day.id}),
            user=planner,
        )
        event_count = Event.objects.all().count()
        form = response.form
        target_date = datetime.now() + timedelta(days=14)
        recurr = recurrence.Recurrence(
            dtstart=datetime.now(),
            rdates=[target_date],
        )
        form["start_date"] = datetime.now().date()
        form["recurrence"] = str(recurr)
        form.submit()
        occurrences = recurr.between(
            datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=365)
        )
        assert Event.objects.all().count() == event_count + 2
        assert Shift.objects.filter(start_time__date__in=occurrences).count() == 2
        for shift_date in occurrences:
            shift = Shift.objects.get(start_time__date=shift_date)
            assert shift.event.title == event_to_next_day.title
            assert shift.event.get_start_time() == shift.start_time
            assert shift.meeting_time.date() == shift.start_time.date()
            assert shift.end_time.date() == shift.start_time.date() + timedelta(days=1)
            assert (volunteers and planners) in get_groups_with_perms(shift.event, ["view_event"])
            assert planners in get_groups_with_perms(shift.event, ["change_event"])
