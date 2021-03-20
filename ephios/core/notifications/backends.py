from django.core.mail import EmailMultiAlternatives
from django.utils.translation import gettext_lazy as _
from webpush import send_user_notification

from ephios.core.models.users import Notification
from ephios.core.signals import register_notification_backends


def installed_notification_backends():
    for _, backends in register_notification_backends.send_to_all_plugins(None):
        yield from (b() for b in backends)


def enabled_notification_backends():
    for _, backends in register_notification_backends.send(None):
        yield from (b() for b in backends)


class AbstractNotificationBackend:
    @property
    def slug(self):
        return NotImplementedError

    @property
    def title(self):
        return NotImplementedError

    @classmethod
    def can_send(cls, notification):
        return notification.user is not None

    @classmethod
    def user_prefers_sending(cls, notification):
        if notification.notification_type.unsubscribe_allowed and notification.user is not None:
            backends = notification.user.preferences["notifications__notifications"].get(
                notification.slug
            )
            if backends is not None:
                return cls.slug in backends
        return True

    @classmethod
    def send(cls, notification: Notification):
        raise NotImplementedError


class EmailNotificationBackend(AbstractNotificationBackend):
    slug = "ephios_backend_email"
    title = _("via email")

    @classmethod
    def can_send(cls, notification):
        return notification.user is not None or "email" in notification.data

    @classmethod
    def _get_mailaddress(cls, notification):
        return notification.user.email if notification.user else notification.data.get("email")

    @classmethod
    def send(cls, notification):
        email = EmailMultiAlternatives(
            to=[cls._get_mailaddress(notification)],
            subject=notification.subject,
            body=notification.as_plaintext(),
        )
        email.attach_alternative(notification.as_html(), "text/html")
        email.send()


class WebPushNotificationBackend(AbstractNotificationBackend):
    slug = "ephios_backend_webpush"
    title = _("via push notification")

    @classmethod
    def send(cls, notification):
        payload = {
            "head": str(notification.subject),
            "body": notification.as_plaintext(),
        }
        send_user_notification(user=notification.user, payload=payload, ttl=1000)


CORE_NOTIFICATION_BACKENDS = [EmailNotificationBackend, WebPushNotificationBackend]
