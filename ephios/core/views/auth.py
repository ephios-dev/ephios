from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    RedirectView,
    UpdateView,
)
from oauthlib.oauth2 import WebApplicationClient
from requests import PreparedRequest, RequestException
from requests_oauthlib import OAuth2Session

from ephios.core.forms.users import OIDCDiscoveryForm
from ephios.core.models.users import EphiosOIDCClient


class OIDCInitiateView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        client = get_object_or_404(EphiosOIDCClient, id=self.kwargs["client"])
        oauth_client = WebApplicationClient(client_id=client.client_id)
        oauth = OAuth2Session(
            client=oauth_client,
            redirect_uri=urljoin(settings.GET_SITE_URL(), reverse("core:oidc_callback")),
            scope=client.scopes,
        )

        authorization_url, state = oauth.authorization_url(client.auth_endpoint)
        self.request.session["oidc_state"] = state
        self.request.session["oidc_client_id"] = client.id
        self.request.session["oidc_login_next"] = self.request.GET.get("next", None)
        return authorization_url


class OIDCCallbackView(RedirectView):
    def failure_url(self):
        messages.error(self.request, _("Authentication failed."))
        return settings.LOGIN_URL

    def get_redirect_url(self, *args, **kwargs):
        if "error" in self.request.GET:
            return self.failure_url()
        if "state" in self.request.GET and "code" in self.request.GET:
            if (
                "oidc_state" not in self.request.session
                or self.request.session.pop("oidc_state") != self.request.GET["state"]
            ):
                return self.failure_url()

            user = auth.authenticate(self.request)

            if user and user.is_active:
                request_user = getattr(self.request, "user", None)
                if not request_user or not request_user.is_authenticated or request_user != user:
                    auth.login(self.request, user)
                return self.request.session.get("oidc_login_next") or "/"
        return self.failure_url()


class OIDCLogoutView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        logout_url = reverse("login")
        if "oidc_client_id" in self.request.session:
            clients = EphiosOIDCClient.objects.filter(id=self.request.session.get("oidc_client_id"))
            if clients.exists() and (client := clients.first()).end_session_endpoint:
                req = PreparedRequest()
                req.prepare_url(
                    client.end_session_endpoint,
                    {"post_logout_redirect_uri": settings.GET_SITE_URL()},
                )
                logout_url = req.url
        auth.logout(self.request)
        messages.info(self.request, _("Logged out successfully."))
        return logout_url


class OIDCClientCreateView(SuccessMessageMixin, CreateView):
    model = EphiosOIDCClient
    fields = [
        "label",
        "client_id",
        "client_secret",
        "scopes",
        "default_groups",
        "auth_endpoint",
        "token_endpoint",
        "user_endpoint",
        "end_session_endpoint",
        "jwks_endpoint",
    ]
    success_url = reverse_lazy("core:settings_oidc_create")
    success_message = _("OIDC client successfully created.")

    def get_initial(self):
        initial = super().get_initial()
        if "url" in self.request.GET:
            try:
                oidc_configuration = requests.get(
                    urljoin(self.request.GET["url"], ".well-known/openid-configuration")
                ).json()
                initial.update(
                    {
                        "auth_endpoint": oidc_configuration["authorization_endpoint"],
                        "token_endpoint": oidc_configuration["token_endpoint"],
                        "user_endpoint": oidc_configuration["userinfo_endpoint"],
                        "end_session_endpoint": oidc_configuration["end_session_endpoint"],
                        "jwks_endpoint": oidc_configuration["jwks_uri"],
                    }
                )
                messages.success(
                    self.request,
                    _(
                        "Successfully fetched OIDC configuration. Please fill in the remaining fields."
                    ),
                )
            except (ConnectionError, RequestException, KeyError):
                messages.warning(
                    self.request,
                    _(
                        "Could not fetch OIDC configuration from the given URL. Please configure the client manually below."
                    ),
                )
        return initial


class OIDCClientDiscoveryView(FormView):
    form_class = OIDCDiscoveryForm
    template_name = "core/ephiosoidcclient_discovery.html"

    def form_valid(self, form):
        return redirect(f"{reverse('core:settings_oidc_create')}?url={form.cleaned_data['url']}")


class OIDCClientListView(ListView):
    model = EphiosOIDCClient


class OIDCClientUpdateView(UpdateView):
    model = EphiosOIDCClient
    fields = [
        "label",
        "client_id",
        "client_secret",
        "scopes",
        "default_groups",
        "auth_endpoint",
        "token_endpoint",
        "user_endpoint",
        "end_session_endpoint",
        "jwks_endpoint",
    ]


class OIDCClientDeleteView(DeleteView):
    model = EphiosOIDCClient
    success_url = reverse_lazy("core:settings_oidc_list")
