from django.urls import reverse

from ephios.core.models import Event


class TestEventBulkDelete:
    def test_empty_list(self, django_app, planner, event, groups):
        event_count = Event.objects.count()
        form = django_app.get(reverse("core:event_list"), user=planner).forms["bulk_action_form"]
        form.action = reverse(
            "core:event_bulk_delete"
        )  # webtest cannot read the formaction from button
        form.submit(name="delete")
        assert event_count == Event.objects.count()

    def test_delete_multiple_events(self, django_app, planner, event, multi_shift_event, groups):
        event_count = Event.objects.count()
        form = django_app.get(reverse("core:event_list"), user=planner).forms["bulk_action_form"]
        form.action = reverse(
            "core:event_bulk_delete"
        )  # webtest cannot read the formaction from button
        form["bulk_action"] = [event.pk, multi_shift_event.pk]
        confirm_page = form.submit(name="delete")
        # assert confirm_page.html.find_all(string=[event.title, multi_shift_event])
        confirm_page.form.submit()
        assert Event.objects.count() == event_count - 2
