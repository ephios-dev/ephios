from django.core import mail
from django.core.mail import EmailMultiAlternatives

from ephios.core.models.users import Notification
from ephios.core.notifications.types import notification_type_from_slug
from ephios.core.signals import register_notification_backends


def all_notification_backends():
    for _, backends in register_notification_backends.send(None):
        yield from (b() for b in backends)


class AbstractBackend:
    def send(self, notifications: list[Notification]):
        raise NotImplementedError


class EmailBackend(AbstractBackend):
    def send(self, notifications):
        email_messages = []
        for notification in notifications:
            handler = notification_type_from_slug(notification.slug)
            email = EmailMultiAlternatives(
                to=[notification.user.email],
                subject=handler.get_subject(notification),
                body=handler.as_plaintext(notification),
            )
            email.attach_alternative(handler.as_html(notification), "text/html")
            email_messages.append(email)
        mail.get_connection().send_messages(email_messages)
