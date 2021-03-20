from django.core.management import BaseCommand

from ephios.core.signals import periodic_signal


class Command(BaseCommand):
    def handle(self, *args, **options):
        periodic_signal.send(self)
