API documentation
=================

ephios provides a REST-API built with Django-Rest-Framework.

Auth
----

You can authenticate against the API in two ways: session based or with an OAuth2 flow.

Session based authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A client can authenticate against the API using `session based authentication <https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication>`_.
This allows to visit API endpoints in the browser and use the API in a similar way as the web interface. Login is required and permissions are checked just like in the web interface.

Token based authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^

ephios acts as an OAuth2 provider which allows to obtain an API token that can be used to authenticate against the API.
To get started, you need to create an OAuth2 application under "OAuth2 applications" in the management section of the settins in your ephios instance.
Set the client type to confidential, the authorization grant type to "authorization-code" and the redirect uri to the url of your client application.
Note down client id and client secret. You can integrate the OAuth2 flow with a library in your preferred language: https://oauth.net/code/

Set the following values in your client application:

======================  =====================================================
CLIENT_ID               client id you created in ephios
CLIENT_SECRET           client secret you created in ephios
AUTHORIZATION_ENDPOINT  https://your-ephios-instance.com/api/oauth/authorize/
TOKEN_ENDPOINT          https://your-ephios-instance.com/api/oauth/token/
======================  =====================================================

You also need to specify which scopes you want to request. The following scopes are available:

==================  =========================================================
PUBLIC_READ         Read public data like events and shifts
PUBLIC_WRITE        Write public data like events and shifts
ME_READ             Read own user profile and personal data
ME_WRITE            Write own user profile and personal data
CONFIDENTIAL_READ   Read confidential data like participations and user data
CONFIDENTIAL_WRITE  Write confidential data like participations and user data
==================  =========================================================

With these values, you should be able to initiate the OAuth2 flow. After the user has authorized your application, you will receive an access token that you can use to authenticate against the API endpoints described below.
You must present the access token in the Authorization header of your requests like this: ``Authorization: Bearer <access token>``

Endpoints
---------

.. openapi:: ephios-open-api-schema.yml