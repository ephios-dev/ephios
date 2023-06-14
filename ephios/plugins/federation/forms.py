import base64
import binascii
import json
from json import JSONDecodeError
from urllib.parse import urljoin

import requests
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext as _
from django_select2.forms import Select2MultipleWidget
from dynamic_preferences.registries import global_preferences_registry
from requests import HTTPError

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
        queryset=FederatedGuest.objects.all(), required=False, widget=Select2MultipleWidget
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "guests")
        self.event = kwargs.pop("event")
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        try:
            self.instance = FederatedEventShare.objects.get(event_id=self.event.id)
        except (AttributeError, FederatedEventShare.DoesNotExist):
            self.instance = FederatedEventShare(event=self.event)
        self.fields["shared_with"].initial = self.instance.shared_with.all()

    def save(self):
        self.instance.shared_with.set(self.cleaned_data["shared_with"])

    @property
    def heading(self):
        return _("Federation")

    def is_function_active(self):
        return self.instance.shared_with.exists()


class InviteCodeForm(forms.ModelForm):
    class Meta:
        model = InviteCode
        fields = ["url"]


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
                redirect_uris=urljoin(
                    data["host_url"], reverse("federation:federation_oauth_callback")
                ),
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
            )
            response.raise_for_status()
            response_data = response.json()
            oauth_application.name = response_data["name"]
            oauth_application.save()
            FederatedHost.objects.create(
                name=response_data["name"],
                url=data["host_url"],
                access_token=response_data["access_token"],
                oauth_application=oauth_application,
            )
        except (binascii.Error, JSONDecodeError, KeyError, HTTPError) as exc:
            raise ValidationError(_("Invalid code")) from exc
