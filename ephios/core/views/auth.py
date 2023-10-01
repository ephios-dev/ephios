from mozilla_django_oidc.views import OIDCAuthenticationRequestView


class OAuthRequestView(OIDCAuthenticationRequestView):
    @staticmethod
    def get_settings(attr, *args):
        test = {
            "OIDC_RP_CLIENT_ID": "3c23327f-416a-4862-b8a8-928d1b7bcfc9",
            "OIDC_OP_AUTHORIZATION_ENDPOINT": "https://oidc.hpi.de/auth",
            "OIDC_AUTHENTICATION_CALLBACK_URL": "oidc_authentication_callback",
            "OIDC_OP_TOKEN_ENDPOINT": "https://oidc.hpi.de/token",
            "OIDC_RP_SCOPES": "openid profile email",
        }
        return test.get(attr, args[0] if args else None)
