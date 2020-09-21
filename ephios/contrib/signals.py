from django.dispatch import receiver

from ephios.contrib.signup.confirm import RequestConfirmSignupMethod
from ephios.contrib.signup.instant import InstantConfirmationSignupMethod
from ephios.event_management.signup import register_signup_methods


@receiver(register_signup_methods, dispatch_uid="ephios.contrib.register_signup_methods")
def register_instant_method(sender, **kwargs):
    return [InstantConfirmationSignupMethod, RequestConfirmSignupMethod]
