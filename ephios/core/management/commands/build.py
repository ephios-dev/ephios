from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "(Re)build static files, language files, directories and VAPID key"

    def handle(self, *args, **options):
        call_command("generate_vapid_key", verbosity=1)
        call_command("collectstatic", verbosity=1, interactive=False)
        call_command("compilemessages", verbosity=1)
        call_command("compilejsi18n", verbosity=1)
