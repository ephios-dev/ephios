import logging

from django.core.management import BaseCommand

from ephios.core.signals import periodic_signal

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run periodic tasks"

    def handle(self, *args, **options):
        logger.info("Running periodic tasks")
        periodic_signal.send(self)
