import logging
from argparse import Namespace
from collections import OrderedDict

from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.services.notifications.types import (
    ResponsibleConfirmedParticipationDeclinedNotification,
    ResponsibleParticipationStateChangeNotification,
)
from ephios.core.signals import register_signup_methods
from ephios.core.signup.flow.builtin.manual import ManualSignupFlow
from ephios.core.signup.participants import AbstractParticipant
from ephios.core.signup.stats import SignupStats
from ephios.extra.utils import format_anything

logger = logging.getLogger(__name__)


def installed_shift_structures():
    return [
        # TODO add more and use signals
    ]
    # for _, methods in register_signup_methods.send_to_all_plugins(None):
    #     yield from methods


def enabled_shift_structures():
    # for _, methods in register_signup_methods.send(None):
    #     yield from methods
    # TODO
    yield from installed_shift_structures()


def shift_structure_from_slug(slug, shift=None, event=None):
    for structure in installed_shift_structures():
        if structure.slug == slug:
            return structure(shift, event=event)
    raise ValueError(_("Shift structure '{slug}' was not found.").format(slug=slug))
