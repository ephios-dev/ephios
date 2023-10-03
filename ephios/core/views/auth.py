from mozilla_django_oidc.views import OIDCAuthenticationRequestView

from ephios.core.models.users import EphiosOIDCClient


class OAuthRequestView(OIDCAuthenticationRequestView):
    def __init__(self, *args, **kwargs):
        self.client = None

    def get(self, request, *args, **kwargs):
        self.client = EphiosOIDCClient.objects.get(id=self.kwargs["client"])
        super().__init__()
        request.session["oidc_client_id"] = self.client.id
        return super().get(request)

    def get_settings(self, attr, *args):
        return self.client and self.client.get_mozilla_oidc_attribute(attr, *args)
