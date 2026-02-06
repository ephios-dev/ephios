from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.utils.translation import gettext_lazy as _


class OIDCLoginForm(AuthenticationForm):
    username = UsernameField(widget=forms.EmailInput(attrs={"autofocus": True}))
    error_messages = {
        "invalid_login": _(
            "The information you entered was wrong. Note that the fields are case-sensitive."
        ),
        "inactive": _("This account is inactive."),
    }
