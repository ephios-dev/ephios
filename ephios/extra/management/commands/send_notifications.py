from django.core.management import BaseCommand

from ephios.core.services.notifications.backends import send_all_notifications


class Command(BaseCommand):
    def handle(self, *args, **options):
        send_all_notifications()
