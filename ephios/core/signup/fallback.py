import functools
import logging

from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ephios.core.models import AbstractParticipation
from ephios.core.signup.checker import BaseSignupActionValidator, ImproperlyConfiguredError
from ephios.core.signup.methods import BaseSignupMethod
from ephios.plugins.basesignup.signup.common import RenderParticipationPillsShiftStateMixin

logger = logging.getLogger(__name__)


def catch_signup_method_fails(default=None):
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


def get_signup_method_failed_error():
    message = _("Signup configuration is invalid!")
    return ImproperlyConfiguredError(mark_safe(f'<span class="text-danger">{message}</span>'))


class FallbackSignupActionValidator(BaseSignupActionValidator):
    def signup_is_disabled(self, method, participant):
        raise get_signup_method_failed_error()

    def get_checkers(self):
        return [self.signup_is_disabled]


class FallbackSignupMethod(RenderParticipationPillsShiftStateMixin, BaseSignupMethod):
    slug = None
    verbose_name = _("Fallback for missing signup methods")
    description = _(
        """This method is used when the original signup method is not installed anymore."""
    )
    uses_requested_state = False
    signup_action_validator_class = FallbackSignupActionValidator

    def _configure_participation(
        self, participation: AbstractParticipation, **kwargs
    ) -> AbstractParticipation:
        raise TypeError(f"{self.__class__} does not support signup")
