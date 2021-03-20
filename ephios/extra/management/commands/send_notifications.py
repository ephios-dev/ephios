from django.core.management import BaseCommand

from ephios.core.notifications.backends import dispatch


class Command(BaseCommand):
    def handle(self, *args, **options):
        dispatch()
