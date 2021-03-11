from django.core.management import BaseCommand

from ephios.core.models.users import Notification
from ephios.core.notifications.backends import all_notification_backends


class Command(BaseCommand):
    def handle(self, *args, **options):
        notifications = Notification.objects.all()
        for backend in all_notification_backends():
            backend.send(notifications)
        notifications.delete()
