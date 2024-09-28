import logging
import smtplib
import traceback
import uuid
from email.utils import formataddr
from typing import Iterable

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import mail_admins
from django.utils.translation import gettext_lazy as _
from pywebpush import WebPushException
from webpush import send_user_notification

from ephios.core.models.users import Notification
from ephios.core.services.mail.send import send_mail
from ephios.extra.i18n import language

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
    CACHE_LOCK_KEY = "notification_sending_running"
    if cache.get(CACHE_LOCK_KEY):
        return
    cache.set(CACHE_LOCK_KEY, str(uuid.uuid4()), timeout=1800)
    backends = set(installed_notification_backends())

    for backend in backends:
        unprocessed_notifications = [
            notification
            for notification in Notification.objects.filter(processing_completed=False).order_by(
                "created_at"
            )
            if backend.slug not in notification.processed_by
        ]
        try:
            backend.send_multiple(unprocessed_notifications)
        except Exception as e:  # pylint: disable=broad-except
            if settings.DEBUG:
                raise e
            try:
                mail_admins(
                    "Notification sending failed",
                    f"Exception: {e}\n{traceback.format_exc()}",
                )
            except smtplib.SMTPConnectError:
                pass  # if the mail backend threw this, mail admin will probably throw this as well
            logger.warning(f"Notification sending failed with {e}")
    mark_complete_processing(backends)
    cache.delete(CACHE_LOCK_KEY)


def mark_complete_processing(backends):
    backend_slugs = {b.slug for b in backends}
    for notification in Notification.objects.filter(processing_completed=False):
        # can't check with __contains as that is not supported by Sqlite
        if set(notification.processed_by) == backend_slugs:
            notification.processing_completed = True
            notification.save()


class AbstractNotificationBackend:
    @property
    def slug(self):
        return NotImplementedError

    @property
    def title(self):
        return NotImplementedError

    @classmethod
    def sending_possible(cls, notification):
        return notification.user is not None

    @classmethod
    def should_send(cls, notification):
        return (
            cls.sending_possible(notification)
            and cls.user_prefers_sending(notification)
            and not (notification.read or notification.is_obsolete)
        )

    @classmethod
    def user_prefers_sending(cls, notification):
        if not notification.user:
            return True
        if not notification.user.is_active or notification.user.email_invalid:
            return False
        if (
            acting_user := notification.data.get("acting_user", None)
        ) and acting_user == notification.user:
            return False
        if not notification.notification_type.unsubscribe_allowed:
            return True
        return [cls.slug, notification.slug] not in notification.user.disabled_notifications

    @classmethod
    def send_multiple(cls, notifications: Iterable[Notification]):
        to_delete = []
        for notification in notifications:
            try:
                if cls.should_send(notification):
                    with language(
                        (notification.user and notification.user.preferred_language) or None
                    ):
                        cls.send(notification)
            except ObjectDoesNotExist:
                to_delete.append(notification.pk)
                continue
            notification.processed_by.append(cls.slug)
            notification.save()
        Notification.objects.filter(pk__in=to_delete).delete()

    @classmethod
    def send(cls, notification: Notification):
        raise NotImplementedError


class EmailNotificationBackend(AbstractNotificationBackend):
    slug = "ephios_backend_email"
    title = _("via email")

    @classmethod
    def sending_possible(cls, notification):
        return notification.user is not None or notification.data.get("email")

    @classmethod
    def _get_mailaddress(cls, notification):
        if notification.user:
            return formataddr((notification.user.get_full_name(), notification.user.email))
        return notification.data.get("email")

    @classmethod
    def send(cls, notification):
        send_mail(
            to=[cls._get_mailaddress(notification)],
            subject=notification.subject,
            plaintext=notification.as_plaintext(),
            html=notification.as_html(),
            is_autogenerated=True,
        )


class WebPushNotificationBackend(AbstractNotificationBackend):
    slug = "ephios_backend_webpush"
    title = _("via push notification")

    @classmethod
    def send(cls, notification):
        try:
            payload = {
                "head": str(notification.subject),
                "body": notification.body,
                "icon": "/static/ephios/img/ephios-symbol-red.svg",
            }
            if actions := notification.get_actions():
                payload["url"] = actions[0][1]
            send_user_notification(user=notification.user, payload=payload, ttl=1000)
        except WebPushException:
            notification.user.webpush_info.all().delete()


CORE_NOTIFICATION_BACKENDS = [EmailNotificationBackend, WebPushNotificationBackend]
