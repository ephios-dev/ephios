import datetime
import logging
import multiprocessing
import traceback
from typing import List

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, mail_admins
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from webpush import send_user_notification

from ephios.core.models.users import Notification

logger = logging.getLogger(__name__)


def installed_notification_backends() -> List["AbstractNotificationBackend"]:
    from ephios.core.signals import register_notification_backends

    for _, backends in register_notification_backends.send_to_all_plugins(None):
        yield from (b() for b in backends)


def enabled_notification_backends():
    from ephios.core.signals import register_notification_backends

    for _, backends in register_notification_backends.send(None):
        yield from (b() for b in backends)


def send_a_notification(backend):
    with transaction.atomic():
        # grab an untried notification and mark it
        if (
            notification := Notification.objects.exclude(backends_tried__has_key=backend.slug)
            .exclude(backends_tried__has_key=backend.slug)
            .first()
        ) is None:
            return
        notification.backends_tried[backend.slug] = False
        notification.save()

    # send it
    if backend.can_send(notification) and backend.user_prefers_sending(notification):
        try:
            backend.send(notification)
        except Exception as e:  # pylint: disable=broad-except
            if settings.DEBUG:
                raise e
            message = f"Notification {notification.pk}: {notification}\nException: {e}\n{traceback.format_exc()}"
            notification.errors[backend.slug] = message
            notification.save()
            mail_admins(f"Sending notification failed using {backend.slug}", message)
            logger.warning(
                f"Notification sending failed for notification object #{notification.pk} ({notification}) for backend {backend} with {e}"
            )
        else:
            notification.backends_tried[backend.slug] = True
            notification.save()


def send_all_notifications():
    def iter_backend_tries():
        for backend in installed_notification_backends():
            notifications = Notification.objects.exclude(backends_tried__has_key=backend.slug)
            for _ in range(
                notifications.count()
            ):  # count is limited to initial amount of notifications
                yield backend

    with multiprocessing.Pool(processes=settings.NOTIFICATION_SENDING_PROCESS_COUNT) as pool:
        pool.map(send_a_notification, iter_backend_tries())


def delete_old_notifications():
    some_time_ago = timezone.now() - datetime.timedelta(
        seconds=settings.NOTIFICATION_RETENTION_SECONDS
    )
    Notification.objects.filter(created_at__lt=some_time_ago).delete()


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
            if not notification.user.is_active:
                return False
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
        if url := notification.get_url():
            payload["url"] = url
        send_user_notification(user=notification.user, payload=payload, ttl=1000)


CORE_NOTIFICATION_BACKENDS = [EmailNotificationBackend, WebPushNotificationBackend]
