from django.dispatch import receiver

from ephios.event_management.signup import register_signup_methods
from ephios.plugins.basesignup.signup.confirm import RequestConfirmSignupMethod
from ephios.plugins.basesignup.signup.instant import InstantConfirmationSignupMethod


@receiver(
    register_signup_methods,
    dispatch_uid="ephios.plugins.basesignup.signals.register_signup_methods",
)
def register_signup_methods(sender, **kwargs):
    return [InstantConfirmationSignupMethod, RequestConfirmSignupMethod]
