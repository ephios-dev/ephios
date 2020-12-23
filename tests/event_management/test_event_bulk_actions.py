import pytest
from django.urls import reverse

from ephios.event_management.models import Event


@pytest.mark.django_db
class TestEventBulkDelete:
    def test_empty_list(self, django_app, planner, event, groups):
        event_count = Event.objects.count()
        form = django_app.get(reverse("event_management:event_list"), user=planner).form
        form.action = reverse(
            "event_management:event_bulk_delete"
        )  # webtest cannot read the formaction from button
        form.submit(name="delete")
        assert event_count == Event.objects.count()

    def test_delete_multiple_events(self, django_app, planner, event, multi_shift_event, groups):
        event_count = Event.objects.count()
        form = django_app.get(reverse("event_management:event_list"), user=planner).form
        form.action = reverse(
            "event_management:event_bulk_delete"
        )  # webtest cannot read the formaction from button
        form["bulk_action"] = [event.pk, multi_shift_event.pk]
        confirm_page = form.submit(name="delete")
        # assert confirm_page.html.findAll(string=[event.title, multi_shift_event])
        confirm_page.form.submit()
        assert Event.objects.count() == event_count - 2
