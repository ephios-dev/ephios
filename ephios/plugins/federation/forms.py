import base64
import binascii
import json
from json import JSONDecodeError
from urllib.parse import urljoin, urlparse

import requests
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import CheckboxSelectMultiple
from django.urls import reverse
from django.utils.translation import gettext as _
from dynamic_preferences.registries import global_preferences_registry
from requests import HTTPError, ReadTimeout

from ephios.api.models import Application
from ephios.core.forms.events import BasePluginFormMixin
from ephios.plugins.federation.models import (
    FederatedEventShare,
    FederatedGuest,
    FederatedHost,
    InviteCode,
)


class EventAllowFederationForm(BasePluginFormMixin, forms.Form):
    shared_with = forms.ModelMultipleChoiceField(
        queryset=FederatedGuest.objects.all(), required=False, widget=CheckboxSelectMultiple
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "federation")
        self.event = kwargs.pop("event")
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        try:
            self.instance = FederatedEventShare.objects.get(event_id=self.event.id)
        except (AttributeError, FederatedEventShare.DoesNotExist):
            self.instance = FederatedEventShare(event=self.event)
        self.fields["shared_with"].initial = (
            self.instance.shared_with.all() if self.instance.pk else []
        )

    def save(self):
        if self.cleaned_data["shared_with"] and not self.instance.pk:
            self.instance.save()
        if self.instance.pk:
            self.instance.shared_with.set(self.cleaned_data["shared_with"])

    @property
    def heading(self):
        return _("Share event with other ephios instances")

    def is_function_active(self):
        return self.instance.pk and self.instance.shared_with.exists()


class InviteCodeForm(forms.ModelForm):
    class Meta:
        model = InviteCode
        fields = ["url"]
        widgets = {
            "url": forms.URLInput(attrs={"placeholder": _("https://other-instance.ephios.de/")})
        }

    def clean_url(self):
        result = urlparse(self.cleaned_data["url"])
        cleaned_result = f"{result.scheme}://{result.netloc}{result.path.strip('/')}"
        return cleaned_result


class RedeemInviteCodeForm(forms.Form):
    code = forms.CharField(label=_("Invite code"))

    def clean_code(self):
        try:
            data = json.loads(
                base64.b64decode(self.cleaned_data["code"].encode("ascii")).decode("ascii")
            )
            if settings.GET_SITE_URL() != data["guest_url"]:
                raise ValidationError(_("This invite code is not issued for this instance."))
            oauth_application = Application(
                client_type=Application.CLIENT_CONFIDENTIAL,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                redirect_uris=urljoin(data["host_url"], reverse("federation:oauth_callback")),
            )
            response = requests.post(
                urljoin(data["host_url"], reverse("federation:redeem_invite_code")),
                data={
                    "name": global_preferences_registry.manager()["general__organization_name"],
                    "url": data["guest_url"],
                    "client_id": oauth_application.client_id,
                    "client_secret": oauth_application.client_secret,
                    "code": data["code"],
                },
                timeout=10,
            )
            response.raise_for_status()
            response_data = response.json()
            oauth_application.name = response_data["host_name"]
            oauth_application.save()
            FederatedHost.objects.create(
                name=response_data["host_name"],
                url=data["host_url"],
                access_token=response_data["access_token"],
                oauth_application=oauth_application,
            )
        except (binascii.Error, JSONDecodeError, KeyError, HTTPError, ReadTimeout) as exc:
            raise ValidationError(_("Invalid code")) from exc
