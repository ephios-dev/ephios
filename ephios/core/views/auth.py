from urllib.parse import urljoin

from django.conf import settings
from django.contrib import auth, messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import RedirectView
from oauthlib.oauth2 import WebApplicationClient
from requests import PreparedRequest
from requests_oauthlib import OAuth2Session

from ephios.core.models.users import EphiosOIDCClient


class OAuthRequestView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        client = get_object_or_404(EphiosOIDCClient, id=self.kwargs["client"])
        oauth_client = WebApplicationClient(client_id=client.client_id)
        oauth = OAuth2Session(
            client=oauth_client,
            redirect_uri=urljoin(settings.GET_SITE_URL(), reverse("core:oauth_callback")),
            scope=client.scopes,
        )

        authorization_url, state = oauth.authorization_url(client.auth_endpoint)
        self.request.session["oidc_state"] = state
        self.request.session["oidc_client_id"] = client.id
        self.request.session["oidc_login_next"] = self.request.GET.get("next", None)
        return authorization_url


class OAuthCallbackView(RedirectView):
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


class OAuthLogoutView(RedirectView):
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
