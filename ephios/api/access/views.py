import binascii
import os

from django import forms
from django.shortcuts import redirect
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView
from guardian.mixins import LoginRequiredMixin
from oauth2_provider.models import get_application_model
from oauth2_provider.scopes import get_scopes_backend
from oauth2_provider.views import ApplicationList

from ephios.api.models import AccessToken
from ephios.extra.mixins import StaffRequiredMixin
from ephios.extra.widgets import CustomSplitDateTimeWidget


class AllUserApplicationList(StaffRequiredMixin, ApplicationList):
    def get_queryset(self):
        return get_application_model().objects.all()


class TokenScopesChoiceField(forms.MultipleChoiceField):
    def clean(self, value):
        scopes_list = super().clean(value)
        return " ".join(scopes_list)

    def to_python(self, value):  # TODO is this correct?
        if isinstance(value, str):
            return value.split(" ")
        return value


class AccessTokenForm(forms.ModelForm):
    scope = TokenScopesChoiceField(
        choices=[
            (scope, mark_safe(f"<code>{scope}</code>: {description}"))
            for scope, description in get_scopes_backend().get_all_scopes().items()
        ],
        widget=forms.CheckboxSelectMultiple,
    )
    expires = forms.SplitDateTimeField(
        widget=CustomSplitDateTimeWidget,
        required=False,
    )

    class Meta:
        model = AccessToken
        fields = ["description", "scope", "expires"]


def generate_key():
    return binascii.hexlify(os.urandom(60)).decode()


class AccessTokenCreateView(LoginRequiredMixin, CreateView):
    model = AccessToken
    form_class = AccessTokenForm
    template_name = "api/access_token_form.html"
    success_message = _(
        "Event type was created. More settings for this event type can be managed below."
    )

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        token = form.save(commit=False)
        token.user = self.request.user
        token.token = generate_key()
        token.save()
        return redirect("oauth2_provider:authorized-token-list")
