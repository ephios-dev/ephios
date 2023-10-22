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
client id                      *displayed after OIDC client registration*
client secret                  *displayed after OIDC client registration*
============================== ===============================================

Configuration
-------------

To configure your ephios instance, head to Settings -> Identity Providers and add a new OIDC provider.
You are then asked to provide the base url of your identity provider. This is the url that is used to access the OIDC endpoints and depends on your provider.
For example, if you are using Keycloak, this would be ``https://your-keycloak-instance.com/realms/your-realm``.
If your provider supports auto-discovery, we will automatically fetch the required information from the OIDC provider.
Otherwise, you will need to provide the following information:

============================== ===============================================
Value                          Usual value
============================== ===============================================
AUTHORIZATION_ENDPOINT         https://your-oidc-provider.com/auth
TOKEN_ENDPOINT                 https://your-oidc-provider.com/token
USERINFO_ENDPOINT              https://your-oidc-provider.com/me
JWKS_URI                       https://your-oidc-provider.com/certs
============================== ===============================================

The following additional configuration options are available:

============================== =================================================== ========================
Value                          Usage                                               Default value
============================== =================================================== ========================
scopes                         Scopes to request from the RP (for additional data) ``openid profile email``
end_session_endpoint           redirect the user to the logout page of the IDP     None (no redirect)
default groups                 groups to add all users logging in with this IDP to None (no groups)
============================== =================================================== ========================

If users are logged in exclusively using identity providers, you can also hide the local login form with the appropriate settings under "ephios instance".

.. warning::
    ephios uses the email adress provided by the IDP to identify a user account. If the IDP allows the user to change their email adress,
    users could enter the email adress of another user and log in as that user. To prevent this, you should configure your IDP to not allow users to change their email adress.

Usage
-----
After you configured at least one identity providers, the login page will display a button for each identity provider.
Clicking on this button will redirect you to the OIDC provider, where you can log in.
To log in with a local user account when the login form is hidden, you can still do so by navigating to ``/accounts/login/?local=true``.

.. toctree::
    :maxdepth: 2
