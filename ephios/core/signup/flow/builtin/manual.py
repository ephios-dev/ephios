from django.utils.translation import gettext_lazy as _

from ephios.core.signup.flow.base import BaseSignupFlow


class ManualSignupFlow(BaseSignupFlow):
    """
    Signup flow for manual signups.
    """

    slug = "manual"
    verbose_name = _("Manual")
    description = _("Sign up by the organizer")
    registration_button_text = _("Sign up")
    uses_requested_state = False

    def _configure_participation(self, participation, **kwargs):
        raise TypeError("Manual signup flow does not support signup.")

    # todo add validator
