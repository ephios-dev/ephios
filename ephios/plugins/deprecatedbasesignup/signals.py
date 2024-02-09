from django.dispatch import receiver

from ephios.core.signup.methods import register_signup_methods
from ephios.plugins.basesignup.signup.coupled_signup import CoupledSignupMethod
from ephios.plugins.basesignup.signup.instant import InstantConfirmationSignupMethod
from ephios.plugins.basesignup.signup.no_selfservice import NoSelfserviceSignupMethod
from ephios.plugins.basesignup.signup.request_confirm import RequestConfirmSignupMethod
from ephios.plugins.basesignup.signup.section_based import SectionBasedSignupMethod


@receiver(
    register_signup_methods,
    dispatch_uid="ephios.plugins.basesignup.signals.register_signup_methods",
)
def register_base_signup_methods(sender, **kwargs):
    return [
        InstantConfirmationSignupMethod,
        RequestConfirmSignupMethod,
        SectionBasedSignupMethod,
        NoSelfserviceSignupMethod,
        CoupledSignupMethod,
    ]
