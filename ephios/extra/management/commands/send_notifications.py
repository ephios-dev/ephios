import traceback

from django.core.mail import mail_admins
from django.core.management import BaseCommand

from ephios.core.models.users import Notification
from ephios.core.notifications.backends import all_notification_backends


class Command(BaseCommand):
    def handle(self, *args, **options):
        for backend in all_notification_backends():
            for notification in Notification.objects.filter(failed=False):
                if backend.can_send(notification) and backend.user_prefers_sending(notification):
                    try:
                        backend.send(notification)
                    except Exception as e:
                        notification.failed = True
                        notification.save()
                        mail_admins(
                            "Notification sending failed",
                            f"Notification: {notification}\nException: {e}\n{traceback.format_exc()}",
                        )
        Notification.objects.filter(failed=False).delete()
