from django.core.mail import EmailMultiAlternatives
from django.utils.translation import gettext_lazy as _
from webpush import send_user_notification

from ephios.core.models.users import Notification
from ephios.core.notifications.types import notification_type_from_slug
from ephios.core.signals import register_notification_backends


def all_notification_backends():
    for _, backends in register_notification_backends.send(None):
        yield from (b() for b in backends)


class AbstractBackend:
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
        notification_type = notification_type_from_slug(notification.slug)
        if notification_type.unsubscribe_allowed and notification.user is not None:
            return cls.slug in notification.user.preferences[f"notifications__{notification.slug}"]
        return True

    @classmethod
    def send(cls, notification: Notification):
        raise NotImplementedError


class EmailBackend(AbstractBackend):
    slug = "ephios_backend_email"
    title = _("via email")

    @classmethod
    def can_send(self, notification):
        return notification.user is not None or "email" in notification.data

    @classmethod
    def _get_mailaddress(cls, notification):
        return notification.user.email if notification.user else notification.data.get("email")

    @classmethod
    def send(cls, notification):
        notification_type = notification_type_from_slug(notification.slug)
        email = EmailMultiAlternatives(
            to=[cls._get_mailaddress(notification)],
            subject=notification_type.get_subject(notification),
            body=notification_type.as_plaintext(notification),
        )
        email.attach_alternative(notification_type.as_html(notification), "text/html")
        email.send()


class WebPushBackend(AbstractBackend):
    slug = "ephios_backend_webpush"
    title = _("via push notification")

    def send(cls, notification):
        notification_type = notification_type_from_slug(notification.slug)
        payload = {
            "head": str(notification_type.get_subject(notification)),
            "body": notification_type.as_plaintext(notification),
        }
        send_user_notification(user=notification.user, payload=payload, ttl=1000)
