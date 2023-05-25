API documentation
=================

ephios provides a REST-API built with Django-Rest-Framework.

Auth
----

You can authenticate against the API using session based authentication or
tokens acquired using the OAuth2 flow or manually from the user settings.

Session based authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A client can authenticate against the API using `session based authentication <https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication>`_.
This allows to visit API endpoints in the browser and use the API in a
similar way as the web interface. Login is required and permissions are
checked just like in the web interface.
This is the recommended way to access the API from interactive ephios
webpages (javascript/AJAX).

Token based authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^

API tokens can be acquired from the user settings page and used in custom
applications or scripts to access the API.
When creating a token you should provide a helpful description as well as set
a fitting expiration date.

ephios uses Scopes to restrict the validity of API tokens to those endpoints
that are needed by the application that uses the token. The scope should be
as narrow as possible to prevent abuse of the token.

The following scopes are available:

==================  =========================================================
PUBLIC_READ         Read public data like available events and shifts
PUBLIC_WRITE        Write public data like available events and shifts
ME_READ             Read own personal data and participations
ME_WRITE            Write own personal data and participations
CONFIDENTIAL_READ   Read confidential data like all users profile and participations
CONFIDENTIAL_WRITE  Write confidential data like all users profile and participations
==================  =========================================================

In your requests to the API the token must be presented in the
Authorization header like this:

``Authorization: Bearer <access token>``

Permissions are checked based on the tokens scope and the permissions of the
user that created the token. For example, if a token with the scope
``PUBLIC_READ`` is used, the token can be used to access the events endpoint,
but only events that are visible to that user will be returned.

.. note:: We plan on integrating API-Keys that are independent of users in the future.

ephios as an OAuth2 provider
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ephios can act as an OAuth2 provider which allows third-party applications to
obtain API tokens for its users. The API tokens acquired using the OAuth2 flow
function just like the manually created ones.

To get started, you need to create an OAuth2 application under
"OAuth2 applications" in the management section of the settings in your
ephios instance.
Set the client type to confidential, the authorization grant type
to "authorization-code" and the redirect uri to the url of your client
application.
Note down client id and client secret. You can integrate the OAuth2 flow
with a library in your preferred language: https://oauth.net/code/

Set the following values in your third-party application:

======================  =====================================================
CLIENT_ID               client id you created in ephios
CLIENT_SECRET           client secret you created in ephios
AUTHORIZATION_ENDPOINT  https://your-ephios-instance.com/api/oauth/authorize/
TOKEN_ENDPOINT          https://your-ephios-instance.com/api/oauth/token/
======================  =====================================================

With these values, you should be able to initiate the OAuth2 flow, where you
also need to specify which scope you want to request from the user.
After the user has authorized your application, you will receive an access token
that you can use to authenticate against the API endpoints described above.

Endpoints
---------

.. openapi:: ephios-open-api-schema.yml