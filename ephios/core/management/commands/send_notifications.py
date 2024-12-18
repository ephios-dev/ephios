from django.core.management import BaseCommand

from ephios.core.services.notifications.backends import send_all_notifications


class Command(BaseCommand):
    help = "Send all notifications (for testing, use run_periodic in production)"

    def handle(self, *args, **options):
        send_all_notifications()
