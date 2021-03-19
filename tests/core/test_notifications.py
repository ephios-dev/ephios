import pytest
from django.core.management import call_command
from django.urls import reverse

from ephios.core.models import Notification
from ephios.core.notifications.backends import enabled_notification_backends
from ephios.core.notifications.types import ProfileUpdateNotification, enabled_notification_types


@pytest.mark.django_db
class TestNotifications:
    def test_notification_form_render(self, django_app, volunteer):
        form = django_app.get(reverse("core:profile_notifications"), user=volunteer).form
        types = filter(
            lambda notification_type: notification_type.unsubscribe_allowed,
            enabled_notification_types(),
        )
        assert all(notification_type.slug in form.fields.keys() for notification_type in types)

    def test_notification_form_submit(self, django_app, volunteer):
        form = django_app.get(reverse("core:profile_notifications"), user=volunteer).form
        form["ephios_new_event"] = ["ephios_backend_email"]
        form.submit()
        assert (
            "ephios_backend_email"
            in volunteer.preferences["notifications__notifications"]["ephios_new_event"]
        )

    def test_notification_sending(self, volunteer):
        ProfileUpdateNotification.send(volunteer)
        preferences = volunteer.preferences["notifications__notifications"]
        preferences["ephios_profile_update"] = enabled_notification_backends()
        call_command("send_notifications")
        assert Notification.objects.count() == 0
