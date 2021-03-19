import logging
import traceback

from django.conf import settings
from django.core.mail import mail_admins
from django.core.management import BaseCommand

from ephios.core.models.users import Notification
from ephios.core.notifications.backends import installed_notification_backends


class Command(BaseCommand):
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
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
                        self.logger.warning(
                            f"Notification sending failed for notification object #{notification.pk} ({notification}) for backend {backend} with {e}"
                        )
        Notification.objects.filter(failed=False).delete()
