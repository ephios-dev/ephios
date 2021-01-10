from django.dispatch import receiver

from ephios.event_management.signup import register_signup_methods
from ephios.plugins.basesignup.signup.section_based import SectionBasedSignupMethod
from ephios.plugins.basesignup.signup.simple import (
    InstantConfirmationSignupMethod,
    RequestConfirmSignupMethod,
)


@receiver(
    register_signup_methods,
    dispatch_uid="ephios.plugins.basesignup.signals.register_signup_methods",
)
def register_base_signup_methods(sender, **kwargs):
    return [InstantConfirmationSignupMethod, RequestConfirmSignupMethod, SectionBasedSignupMethod]
