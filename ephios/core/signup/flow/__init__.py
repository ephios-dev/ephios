import logging

from django.utils.translation import gettext_lazy as _

from ephios.core.signals import register_signup_flows

logger = logging.getLogger(__name__)


def _builitin_flows():
    from ephios.core.signup.flow.builtin.coupled import CoupledSignupFlow
    from ephios.core.signup.flow.builtin.manual import ManualSignupFlow
    from ephios.core.signup.flow.builtin.participant import (
        InstantConfirmSignupFlow,
        RequestConfirmSignupFlow,
    )

    yield from iter(
        [
            ManualSignupFlow,
            RequestConfirmSignupFlow,
            InstantConfirmSignupFlow,
            CoupledSignupFlow,
        ]
    )


def installed_signup_flows():
    yield from _builitin_flows()
    for _, methods in register_signup_flows.send_to_all_plugins(None):
        yield from methods


def enabled_signup_flows():
    yield from _builitin_flows()
    for _, flows in register_signup_flows.send(None):
        yield from flows


def signup_flow_from_slug(slug, shift=None, event=None):
    for flow in installed_signup_flows():
        if flow.slug == slug:
            return flow(shift, event=event)
    raise ValueError(_("Signup Flow '{slug}' was not found.").format(slug=slug))
