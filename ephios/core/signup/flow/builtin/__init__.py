from django.utils.translation import gettext as _

from ephios.core.signup.flow.participant_validation import (
    ActionDisallowedError,
    BaseSignupActionValidator,
)


class NoSignupSignupActionValidator(BaseSignupActionValidator):
    def get_no_signup_allowed_message(self):
        return _("Signup for this shift is disabled.")

    def signup_is_disabled(self, method, participant):
        raise ActionDisallowedError(self.get_no_signup_allowed_message())

    def get_checkers(self):
        return [self.signup_is_disabled]
