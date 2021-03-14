from django.core.mail import EmailMultiAlternatives

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
        if notification.user is not None:
            return cls.slug in notification.user.preferences[f"notifications__{notification.slug}"]
        return True

    @classmethod
    def send(cls, notification: Notification):
        raise NotImplementedError


class EmailBackend(AbstractBackend):
    slug = "ephios_backend_email"
    title = "via email"

    def can_send(self, notification):
        return notification.user is not None or "email" in notification.data

    def get_mailaddress(self, notification):
        return notification.user.email if notification.user else notification.data.get("email")

    def send(self, notification):
        handler = notification_type_from_slug(notification.slug)
        email = EmailMultiAlternatives(
            to=[self.get_mailaddress(notification)],
            subject=handler.get_subject(notification),
            body=handler.as_plaintext(notification),
        )
        email.attach_alternative(handler.as_html(notification), "text/html")
        email.send()
