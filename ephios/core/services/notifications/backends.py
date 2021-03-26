import logging
import traceback

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, mail_admins
from django.utils.translation import gettext_lazy as _
from webpush import send_user_notification

from ephios.core.models.users import Notification

logger = logging.getLogger(__name__)


def installed_notification_backends():
    from ephios.core.signals import register_notification_backends

    for _, backends in register_notification_backends.send_to_all_plugins(None):
        yield from (b() for b in backends)


def enabled_notification_backends():
    from ephios.core.signals import register_notification_backends

    for _, backends in register_notification_backends.send(None):
        yield from (b() for b in backends)


def send_all_notifications():
    for backend in installed_notification_backends():
        for notification in Notification.objects.filter(failed=False):
            if backend.can_send(notification) and backend.user_prefers_sending(notification):
                try:
                    backend.send(notification)
                except Exception as e:  # pylint: disable=broad-except
                    if settings.DEBUG:
                        raise e
                    notification.failed = True
                    notification.save()
                    mail_admins(
                        "Notification sending failed",
                        f"Notification: {notification}\nException: {e}\n{traceback.format_exc()}",
                    )
                    logger.warning(
                        f"Notification sending failed for notification object #{notification.pk} ({notification}) for backend {backend} with {e}"
                    )
    Notification.objects.filter(failed=False).delete()


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
