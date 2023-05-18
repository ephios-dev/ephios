from django.dispatch import receiver

from ephios.core.signals import periodic_signal


@receiver(periodic_signal, dispatch_uid="ephios.api.signals.clear_expired_tokens")
def clear_expired_tokens(sender, **kwargs):
    from oauth2_provider.models import clear_expired

    clear_expired()
