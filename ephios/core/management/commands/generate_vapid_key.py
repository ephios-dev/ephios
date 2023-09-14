import os.path

from django.conf import settings
from django.core.management import BaseCommand
from py_vapid import Vapid


class Command(BaseCommand):
    help = "Generate VAPID key at VAPID_PRIVATE_KEY_PATH if it does not exist"

    def handle(self, *args, **options):
        if not os.path.exists(settings.VAPID_PRIVATE_KEY_PATH):
            print("Generating VAPID key")
            vapid = Vapid()
            vapid.generate_keys()
            vapid.save_key(settings.VAPID_PRIVATE_KEY_PATH)
            vapid.save_public_key(settings.VAPID_PRIVATE_KEY_PATH + ".pub")
            print(f"Saved to {settings.VAPID_PRIVATE_KEY_PATH}")
        else:
            print(f"VAPID key already exists at {settings.VAPID_PRIVATE_KEY_PATH}")
