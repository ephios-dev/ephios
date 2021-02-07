from django.dispatch import receiver

from ephios.plugins.basesignup.signup.instant import InstantConfirmationSignupMethod
from ephios.plugins.basesignup.signup.request_confirm import RequestConfirmSignupMethod
from ephios.plugins.basesignup.signup.section_based import SectionBasedSignupMethod
from ephios.user_management.signup import register_signup_methods


@receiver(
    register_signup_methods,
    dispatch_uid="ephios.plugins.basesignup.signals.register_signup_methods",
)
def register_base_signup_methods(sender, **kwargs):
    return [InstantConfirmationSignupMethod, RequestConfirmSignupMethod, SectionBasedSignupMethod]
