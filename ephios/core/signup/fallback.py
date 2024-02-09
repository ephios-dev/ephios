import functools
import logging

from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup.flow.base import BaseSignupFlow
from ephios.core.signup.flow.participant_validation import (
    BaseSignupActionValidator,
    ImproperlyConfiguredError,
)
from ephios.core.signup.structure.base import BaseShiftStructure

logger = logging.getLogger(__name__)


def default_on_exception(default=None):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception:  # pylint: disable=broad-except
                logger.exception(f"Function {f} in {f.__module__} errored")
                return default() if callable(default) else default

        return decorated

    return decorator


def get_signup_config_invalid_error():
    message = _("Signup configuration is invalid!")
    return ImproperlyConfiguredError(mark_safe(f'<span class="text-danger">{message}</span>'))


class FallbackSignupActionValidator(BaseSignupActionValidator):
    def signup_is_disabled(self, method, participant):
        raise get_signup_config_invalid_error()

    def get_checkers(self):
        return [self.signup_is_disabled]


class FallbackSignupFlow(BaseSignupFlow):
    slug = None
    verbose_name = _("Fallback for missing signup flows")
    description = _("""This flow is used when the original signup flow is not installed anymore.""")
    uses_requested_state = False
    signup_action_validator_class = FallbackSignupActionValidator

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        raise TypeError(f"{self.__class__} does not support signup")


class FallbackShiftStructure(BaseShiftStructure):
    slug = None
    verbose_name = _("Fallback for missing shift structures")
    description = _(
        """This structure is used when the original shift structure is not installed anymore."""
    )
