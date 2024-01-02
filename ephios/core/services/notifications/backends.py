import logging
import smtplib
import traceback

from django.conf import settings
from django.core.mail import mail_admins
from django.utils.translation import gettext_lazy as _
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
    for backend in installed_notification_backends():
        for notification in Notification.objects.filter(failed=False):
            if backend.can_send(notification) and backend.user_prefers_sending(notification):
                with language((notification.user and notification.user.preferred_language) or None):
                    try:
                        backend.send(notification)
                    except Exception as e:  # pylint: disable=broad-except
                        if settings.DEBUG:
                            raise e
                        notification.failed = True
                        notification.save()
                        try:
                            mail_admins(
                                "Notification sending failed",
                                f"Notification: {notification}\nException: {e}\n{traceback.format_exc()}",
                            )
                        except smtplib.SMTPConnectError:
                            pass  # if the mail backend threw this, mail admin will probably throw this as well
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
        if notification.user:
            return f'"{notification.user.get_full_name()}" <{notification.user.email}>'
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
        payload = {
            "head": str(notification.subject),
            "body": notification.body,
            "icon": "/static/ephios/img/ephios-symbol-red.svg",
        }
        if actions := notification.get_actions():
            payload["url"] = actions[0][1]
        send_user_notification(user=notification.user, payload=payload, ttl=1000)


CORE_NOTIFICATION_BACKENDS = [EmailNotificationBackend, WebPushNotificationBackend]
