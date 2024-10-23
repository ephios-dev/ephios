from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.views import LoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import urlencode
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
from dynamic_preferences.registries import global_preferences_registry
from oauthlib.oauth2 import WebApplicationClient
from requests import PreparedRequest, RequestException
from requests_oauthlib import OAuth2Session

from ephios.core.dynamic_preferences_registry import LoginRedirectToSoleIndentityProvider
from ephios.core.forms.auth import OIDCLoginForm
from ephios.core.forms.users import IdentityProviderForm, OIDCDiscoveryForm
from ephios.core.models.users import IdentityProvider
from ephios.extra.mixins import StaffRequiredMixin


class OIDCInitiateView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        provider = get_object_or_404(IdentityProvider, id=self.kwargs["provider"])

        # we are using the OAuth2 tooling here to generate the authorization URL
        oauth_client = WebApplicationClient(client_id=provider.client_id)
        oauth = OAuth2Session(
            client=oauth_client,
            redirect_uri=urljoin(settings.GET_SITE_URL(), reverse("core:oidc_callback")),
            scope=provider.scopes,
        )

        authorization_url, state = oauth.authorization_url(provider.authorization_endpoint)
        self.request.session["oidc_state"] = state
        self.request.session["oidc_provider"] = provider.id
        self.request.session["oidc_login_next"] = self.request.GET.get("next", None)
        return authorization_url


class OIDCCallbackView(RedirectView):
    def failure_url(self):
        messages.error(self.request, _("Authentication failed."))
        return reverse("login")

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
        if "oidc_provider" in self.request.session:
            providers = IdentityProvider.objects.filter(
                id=self.request.session.get("oidc_provider")
            )
            if providers.exists() and (provider := providers.first()).end_session_endpoint:
                auto_provider_redirect = global_preferences_registry.manager()[
                    "general__login_redirect_to_sole_identity_provider"
                ]
                req = PreparedRequest()
                req.prepare_url(
                    provider.end_session_endpoint,
                    # do not send a post_logout_redirect_uri when auto-redirect is on to prevent a loop
                    (
                        {}
                        if auto_provider_redirect
                        else {
                            "post_logout_redirect_uri": settings.GET_SITE_URL(),
                            "client_id": provider.client_id,
                        }
                    ),
                )
                logout_url = req.url
        auth.logout(self.request)
        messages.info(self.request, _("Logged out successfully."))
        return logout_url


class OIDCLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True
    form_class = OIDCLoginForm

    def get(self, request, *args, **kwargs):
        if (
            not self._show_login_form
            and self._providers.count() == 1
            and global_preferences_registry.manager()[
                f"general__{LoginRedirectToSoleIndentityProvider.name}"
            ]
        ):
            provider = self._providers.get()
            redirect_url = reverse("core:oidc_initiate", args=(provider.id,))
            if next_param := self.request.GET.get("next"):
                redirect_url += f"?next={urlencode(next_param)}"
            return redirect(redirect_url)
        return super().get(request, *args, **kwargs)

    @property
    def _providers(self):
        return IdentityProvider.objects.all()

    @property
    def _show_login_form(self):
        return (
            not global_preferences_registry.manager()["general__hide_login_form"]
            or not self._providers.exists()
            or self.request.GET.get("local")
        )

    @property
    def extra_context(self):
        return {
            "providers": self._providers,
            "show_login_form": self._show_login_form,
        }


class IdentityProviderCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = IdentityProvider
    form_class = IdentityProviderForm
    success_url = reverse_lazy("core:settings_idp_list")
    success_message = _("Identity provider saved.")

    def get_initial(self):
        initial = super().get_initial()
        if not self.request.POST and "url" in self.request.GET:
            try:
                oidc_configuration = requests.get(
                    urljoin(self.request.GET["url"], ".well-known/openid-configuration"), timeout=10
                ).json()
                config_keys = [
                    "authorization_endpoint",
                    "token_endpoint",
                    "userinfo_endpoint",
                    "end_session_endpoint",
                    "jwks_uri",
                ]
                initial.update({k: oidc_configuration[k] for k in config_keys})
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


class IdentityProviderDiscoveryView(StaffRequiredMixin, FormView):
    form_class = OIDCDiscoveryForm
    template_name = "core/identityprovider_discovery.html"

    def form_valid(self, form):
        return redirect(f"{reverse('core:settings_idp_create')}?url={form.cleaned_data['url']}")


class IdentityProviderListView(StaffRequiredMixin, ListView):
    model = IdentityProvider


class IdentityProviderUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = IdentityProvider
    form_class = IdentityProviderForm
    success_url = reverse_lazy("core:settings_idp_list")
    success_message = _("Identity provider saved.")


class IdentityProviderDeleteView(StaffRequiredMixin, DeleteView):
    model = IdentityProvider
    success_url = reverse_lazy("core:settings_idp_list")
