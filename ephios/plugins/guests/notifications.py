from urllib.parse import urljoin

from django.utils.translation import gettext_lazy as _
from dynamic_preferences.registries import global_preferences_registry

from ephios.core.dynamic import dynamic_settings
from ephios.core.models import Notification
from ephios.core.services.notifications.types import AbstractNotificationHandler


class GuestUserSignupNotification(AbstractNotificationHandler):
    slug = "guests_signup"
    title = _("A guest user has signed up")
    unsubscribe_allowed = False

    @classmethod
    def send(cls, **kwargs):
        Notification.objects.create(slug=cls.slug, data=kwargs)

    @classmethod
    def get_subject(cls, notification):
        return _("You have signed up for {event}").format(event=notification.data["event_title"])

    @classmethod
    def get_body(cls, notification):
        return _(
            "You have signed up for {event} at {platform}. You can use the link below to make changes to your participation."
        ).format(
            event=notification.data["event_title"],
            platform=global_preferences_registry.manager()["general__organization_name"],
        )

    @classmethod
    def get_actions(cls, notification):
        return [
            (
                str(_("View event")),
                urljoin(dynamic_settings.SITE_URL, notification.data["event_url"]),
            )
        ]
