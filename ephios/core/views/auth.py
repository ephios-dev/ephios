from urllib.parse import urljoin

from django.conf import settings
from django.contrib import auth, messages
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import RedirectView
from oauthlib.oauth2 import WebApplicationClient
from requests_oauthlib import OAuth2Session

from ephios.core.models.users import EphiosOIDCClient


class OAuthRequestView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        client = EphiosOIDCClient.objects.get(id=self.kwargs["client"])
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
            if "oidc_state" not in self.request.session:
                return self.failure_url()
            self.request.session.pop("oidc_state")

        user = auth.authenticate(self.request)

        if user and user.is_active:
            request_user = getattr(self.request, "user", None)
            if not request_user or not request_user.is_authenticated or request_user != user:
                auth.login(self.request, user)
            return self.request.session.get("oidc_login_next") or "/"
        return self.failure_url()
