Configuration options
=====================

Ephios is configured via environment variables. Its often easiest to create a `.env` file and point ephios to it
via the `ENV_PATH` environment variable.

Most variables have a corresponding django setting.
See the `django docs <https://docs.djangoproject.com/en/4.2/ref/settings/>`__
for a more in-depth explanation of what they do.

.. _env_file_options:

The following variables are available (plugins and some niche features might require additional environment variables):

`ENV_PATH`:
    Path to an environment file. Defaults to `.env` in the location of the ephios package.
    We recommend setting most of the following variables in this file.

`SECRET_KEY`:
    **Required**. Django secret key used to encrypt session data and other sensitive information.

`DEBUG`:
    **Required**. Set to `True` to enable debug mode. Must be `False` in production.

`ALLOWED_HOSTS`:
    **Required**. Comma-separated list of hostnames that are allowed to access the ephios instance.

`DATABASE_URL`:
    **Required**. URL to the database. See
    `django-environ <https://django-environ.readthedocs.io/en/latest/types.html#environ-env-db-url>`__ for details.

`SITE_URL`:
    **Required**. URL used to construct absolute URLs in emails and other places.

`CACHE_URL`:
    URL to the cache. See
    `django-environ <https://django-environ.readthedocs.io/en/latest/types.html#environ-env-cache-url>`__ for details.

`STATIC_ROOT`:
    **Required**: Path where static files are collected to.
    A reverse proxy should be configured to serve them at `STATIC_URL`.

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

`LOGGING_FILE`:
    Path to the log file. If provided, ephios logs to this file.
    The file is rotated daily.

`LOGGING_BACKUP_DAYS`:
    Number of days to keep log files. Defaults to 14.

`STATIC_URL`:
    URL where the static files can be found by browsers.
    Defaults to ``/static/``, meaning they are served by the same host.

`DEBUG_TOOLBAR`:
    Set to `True` to enable the django debug toolbar. Must be `False` in production.

`INTERNAL_IPS`:
    Comma-separated list of IP addresses that are allowed to access the debug toolbar.

`VAPID_PRIVATE_KEY_PATH`:
    Path to the private key used to sign web push notifications. If not provided, web push notifications wont work
    on some platforms. See :ref:`web_push_notifications` for details.

`DJANGO_SETTINGS_MODULE`:
    Defaults to `ephios.settings`. If you want to use your own settings file,
    set this to the path to your settings file. This variable cannot be set in the environment file.
