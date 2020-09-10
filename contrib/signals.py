from django.dispatch import receiver

from contrib import signup
from contrib.signup.confirm import RequestConfirmSignupMethod
from contrib.signup.instant import InstantConfirmationSignupMethod
from event_management.signup import register_signup_methods


@receiver(register_signup_methods, dispatch_uid="jep.contrib.register_signup_methods")
def register_instant_method(sender, **kwargs):
    return [InstantConfirmationSignupMethod, RequestConfirmSignupMethod]
