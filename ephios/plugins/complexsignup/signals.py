from django.dispatch import receiver

from ephios.core.signup.methods import register_signup_methods


@receiver(
    register_signup_methods,
    dispatch_uid="ephios.plugins.complexsignup.signals.register_complex_signup_method",
)
def register_complex_signup_method(sender, **kwargs):
    return []
