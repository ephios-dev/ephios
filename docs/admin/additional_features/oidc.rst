SSO / OIDC client
=================

Apart from creating local user accounts, you can also use external identity providers to authenticate your users. This is done by using the OpenID Connect protocol (OIDC), which is built on top of the OAuth 2.0 protocol. This guide will show you how to configure your application to use an external OIDC provider to authenticate your users.

Prerequisites
-------------
You need to have an OIDC provider that you can use. OIDC support is built into a lot of identity providers, but you can also use a dedicated OIDC provider like `Keycloak <https://www.keycloak.org/>`_.
You also need to register a client with your OIDC provider. This client will be used by your application to authenticate with the OIDC provider. The exact steps to do this will vary depending on your OIDC provider, but you will need to provide the following information:

============ ===============================================
Redirect URI https://your-ephios-instance.com/oidc/callback/
============ ===============================================

You will also need to know the following information about your OIDC provider:

============================== ===============================================
Value                          Usual value
============================== ===============================================
OIDC_RP_CLIENT_ID              *displayed after OIDC client registration*
OIDC_RP_CLIENT_SECRET          *displayed after OIDC client registration*
OIDC_RP_SIGN_ALGO              RS256
OIDC_OP_AUTHORIZATION_ENDPOINT https://your-oidc-provider.com/auth
OIDC_OP_TOKEN_ENDPOINT         https://your-oidc-provider.com/token
OIDC_OP_USER_ENDPOINT          https://your-oidc-provider.com/me
OIDC_OP_JWKS_ENDPOINT          https://your-oidc-provider.com/certs
============================== ===============================================

These values as well as ``ENABLE_OIDC_CLIENT=True`` must be provided to the ephios configuration as environment variables.
After completing these steps, users will see a "Login" button that starts the OIDC authentication flow. If you want to
log in with a local user account, you can still do so by navigating to ``/accounts/login/?local=true``.

The following additional configuration options are available:

============================== =================================================== ========================
Value                          Usage                                               Default value
============================== =================================================== ========================
OIDC_RP_SCOPES                 Scopes to request from the RP (for additional data) ``openid profile email``
LOGOUT_REDIRECT_URL            redirect the user to the RP logout page             None (no redirect)
============================== =================================================== ========================

.. toctree::
    :maxdepth: 2
