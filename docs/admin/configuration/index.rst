Configuration options
=====================

Ephios is configured via environment variables. Its often easiest to create a `.env` file and point ephios to it
via the `ENV_PATH` environment variable.

Most variables have a corresponding django setting.
See the `django docs <https://docs.djangoproject.com/en/4.2/ref/settings/>`__
for a more in-depth explanation of what they do.

.. _env_file_options:

The following variables are available (plugins and some niche features might require additional environment variables).

Setup
-----

`ENV_PATH`:
    Path to an environment file. Defaults to `.env` in the location of the ephios package.
    We recommend setting most of the following variables in this file.

`DJANGO_SETTINGS_MODULE`:
    Defaults to `ephios.settings`. If you want to use your own settings file,
    set this to the path to your settings file. This variable cannot be set in the environment file.

Debugging
---------

`DEBUG`:
    **Required**. Set to `True` to enable debug mode. Must be `False` in production.

`DEBUG_TOOLBAR`:
    Set to `True` to enable the django debug toolbar. Must be `False` in production.
    Defaults to `False`.

`INTERNAL_IPS`:
    Comma-separated list of IP addresses that are allowed to access the debug toolbar.
    Defaults to `127.0.0.1`.

Secrets
-------

`SECRET_KEY`:
    **Important**. Django secret key used to encrypt session data and other sensitive information.
    Defaults to a random value persisted into `PRIVATE_DIR/.secret`.

`VAPID_PRIVATE_KEY_PATH`:
    Path to the private key used to sign web push notifications. If not provided, web push notifications wont work
    on some platforms. See :ref:`web_push_notifications` for details.
    Defaults to `PRIVATE_DIR/vapid_key.pem`. A keypair is automatically generated if it does not exist.

Data storage and Logging
------------------------

`DATA_DIR`:
    **Important**. Base path where ephios defaults to store files.
    Defaults to a `data` folder in the location of the ephios package,
    which is not recommended for production use.

`PUBLIC_DIR`:
    Path where public files are stored. Defaults to `DATA_DIR/public`.

`STATIC_ROOT`:
    Path where static files (css/js) are collected to.
    A reverse proxy should be configured to serve them at `STATIC_URL`.
    Defaults to `PUBLIC_DIR/static`.

`PRIVATE_DIR`:
    Path where private files are stored. Defaults to `DATA_DIR/private`.
    Make sure access to this folder is restricted to the user running ephios.

`MEDIA_ROOT`:
    Path where uploaded files are stored.
    Defaults to `PRIVATE_DIR/media`.
    You should backup this folder regularly.

`LOG_DIR`:
    Path to the folder where log files are put. Files inside are rotated daily.
    Defaults to `PRIVATE_DIR/logs`.

`LOGGING_BACKUP_DAYS`:
    Number of days to keep log files. Defaults to 14.


Database and Caching
--------------------

`DATABASE_URL`:
    **Required**. URL to the database. See
    `django-environ <https://django-environ.readthedocs.io/en/latest/types.html#environ-env-db-url>`__ for details.

`CONN_MAX_AGE`:
    Number of seconds to keep database connections open. Defaults to 0, meaning connections are closed after each request.
    Refer to the `django docs <https://docs.djangoproject.com/en/4.2/ref/databases/#persistent-database-connections>`__ for details.

`CACHE_URL`:
    URL to the cache. We recommend redis. See
    `django-environ <https://django-environ.readthedocs.io/en/latest/types.html#environ-env-cache-url>`__ for details.

URLs and Routing
----------------

`ALLOWED_HOSTS`:
    **Required**. Comma-separated list of hostnames that are allowed to access the ephios instance.


`SITE_URL`:
    **Required**. URL used to construct absolute URLs in emails and other places.

`STATIC_URL`:
    URL where the static files can be found by browsers.
    Defaults to ``/static/``, meaning they are served by the same host.

`MEDIA_URL`:
    URL where the media files (meaning files uploaded by users) can be found by browsers.
    Defaults to ``/usercontent/``, meaning they are served by the same host.
    This is NOT recommended for `security reasons <https://docs.djangoproject.com/en/5.1/topics/security/#user-uploaded-content>`__.
    ephios takes care of necessary redirects if this is set to a different domain.
    Please not that if MEDIA_URL is reacheable from the internet, anyone can download media files.
    To prevent this, ephios checks appropriate permissions before serving files. The recommended setup is to
    declare this URL as internal in your reverse proxy and serve the files directly from the filesystem.
    ephios will issue a redirect to the correct URL after checking the permissions.

`FALLBACK_MEDIA_SERVING`:
    If set to `True`, ephios will serve media files itself if the webserver does not.
    This is not recommended for production use. Defaults to `False`.
    Currently only nginx with the X-Accel-Redirect header is supported to serve media files.

Security
--------


`SECURE_HSTS_SECONDS`:
    Number of seconds to set the `Strict-Transport-Security <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security>`__
    header to. Defaults to the amount of seconds in 1 day, but should be set to a higher value in production.

`SECURE_HSTS_INCLUDE_SUBDOMAINS`:
    Include subdomains in the `Strict-Transport-Security <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security>`__
    header. Defaults to `False`.

`SECURE_HSTS_PRELOAD`:
    Set the `preload <https://hstspreload.org/>`__ flag in the `Strict-Transport-Security <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security>`__
    header. Defaults to `False`.

`TRUST_X_FORWARDED_PROTO`:
    ephios must be served over HTTPS in production. In some setups, ephios is behind a reverse proxy that terminates
    SSL connections and the Origin header is not set with a https scheme. In this case, the proxy can communicate
    the fact that the connection is secure by setting the
    `X-Forwarded-Proto <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-Proto>`__ header.
    Then this setting must be set to `True`. See
    `django docs <https://docs.djangoproject.com/en/4.2/ref/settings/#std:setting-SECURE_PROXY_SSL_HEADER>`__
    for details. Defaults to `False`.

E-Mail
------

`EMAIL_URL`:
    **Required**. URL to the email smtp server. See
    `django-environ <https://django-environ.readthedocs.io/en/latest/types.html#environ-env-email-url>`__ for details.

`DEFAULT_FROM_EMAIL`:
    **Required**. Email address that is used as the sender for all
    emails sent by ephios. (`Django docs <https://docs.djangoproject.com/en/4.2/ref/settings/#default-from-email>`__)

`SERVER_EMAIL`:
    **Required**. Email address that is used as the sender for all
    error emails sent by django. (`Django docs <https://docs.djangoproject.com/en/4.2/ref/settings/#server-email>`__)

`ADMINS`:
    **Required**. Email addresses that receive error emails.
