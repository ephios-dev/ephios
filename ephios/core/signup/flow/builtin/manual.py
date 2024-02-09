from django.utils.translation import gettext_lazy as _

from ephios.core.signup.flow.base import BaseSignupFlow


class ManualSignupFlow(BaseSignupFlow):
    """
    Signup flow for manual signups.
    """

    @property
    def slug(self):
        return "manual"

    @property
    def verbose_name(self):
        return _("Manual")

    @property
    def description(self):
        return _("Sign up by the organizer")

    @property
    def registration_button_text(self):
        return _("Sign up")

    @property
    def uses_requested_state(self):
        return False
