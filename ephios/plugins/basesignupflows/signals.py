from django.dispatch import receiver

from ephios.core.signals import register_signup_flows
from ephios.plugins.basesignupflows.flow.coupled import CoupledSignupFlow
from ephios.plugins.basesignupflows.flow.manual import ManualSignupFlow
from ephios.plugins.basesignupflows.flow.participant import (
    InstantConfirmSignupFlow,
    RequestConfirmSignupFlow,
)


@receiver(
    register_signup_flows,
    dispatch_uid="ephios.plugins.basesignupflows.signals.register_base_signup_flows",
)
def register_base_signup_flows(sender, **kwargs):
    return [
        InstantConfirmSignupFlow,
        RequestConfirmSignupFlow,
        ManualSignupFlow,
        CoupledSignupFlow,
    ]
