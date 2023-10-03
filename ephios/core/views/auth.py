from mozilla_django_oidc.views import OIDCAuthenticationRequestView

from ephios.core.models.users import EphiosOIDCClient


class OAuthRequestView(OIDCAuthenticationRequestView):
    def get(self, request, *args, **kwargs):
        self.client = EphiosOIDCClient.objects.get(id=self.kwargs["client"])
        self.OIDC_OP_AUTH_ENDPOINT = self.get_settings("OIDC_OP_AUTHORIZATION_ENDPOINT")
        self.OIDC_RP_CLIENT_ID = self.get_settings("OIDC_RP_CLIENT_ID")
        request.session["oidc_client_id"] = self.client.id
        return super().get(request)

    def get_settings(self, attr, *args):
        return (
            self.client.get_mozilla_oidc_attribute(attr, *args) if hasattr(self, "client") else ""
        )
