import copy
import datetime
import os
import shutil
from datetime import timedelta
from email.utils import getaddresses
from importlib import metadata
from pathlib import Path

import environ
from cryptography.hazmat.primitives import serialization
from django.contrib.messages import constants
from django.utils.translation import gettext_lazy
from py_vapid import Vapid, b64urlencode

from ephios.extra.secrets import django_secret_from_file

# BASE_DIR is the directory containing the ephios package
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


env = environ.Env()
# for syntax see https://django-environ.readthedocs.io/en/latest/
# read env file from ENV_PATH or fall back to a .env file in the project root
env_path = env.str("ENV_PATH", default=os.path.join(BASE_DIR, ".env"))
print(f"Loading ephios environment from {Path(env_path).absolute()}")
environ.Env.read_env(env_file=env_path)

DEBUG = env.bool("DEBUG")

DATA_DIR = env.str("DATA_DIR", os.path.join(BASE_DIR, "data"))
PUBLIC_DIR = env.str("PUBLIC_DIR", os.path.join(DATA_DIR, "public"))
STATIC_ROOT = env.str("STATIC_ROOT", os.path.join(PUBLIC_DIR, "static"))

PRIVATE_DIR = env.str("PRIVATE_DIR", os.path.join(DATA_DIR, "private"))
LOG_DIR = env.str("LOG_DIR", os.path.join(PRIVATE_DIR, "logs"))
MEDIA_ROOT = env.str("MEDIA_ROOT", os.path.join(PRIVATE_DIR, "media"))

DIRECTORIES = {
    "DATA_DIR": DATA_DIR,
    "PUBLIC_DIR": PUBLIC_DIR,
    "STATIC_ROOT": STATIC_ROOT,
    "PRIVATE_DIR": PRIVATE_DIR,
    "LOG_DIR": LOG_DIR,
    "MEDIA_ROOT": MEDIA_ROOT,
}
for directory in DIRECTORIES.values():
    os.makedirs(directory, exist_ok=True)

if "SECRET_KEY" in env:
    SECRET_KEY = env.str("SECRET_KEY")
else:
    SECRET_FILE = os.path.join(PRIVATE_DIR, ".secret")
    SECRET_KEY = django_secret_from_file(SECRET_FILE)


ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

try:
    EPHIOS_VERSION = metadata.version("ephios")
except metadata.PackageNotFoundError:
    # ephios is not installed as a package (e.g. development setup)
    EPHIOS_VERSION = "dev"

INSTALLED_APPS = [
    # we need to import our own modules before everything else to allow template
    # customizing e.g. for django-oauth-toolkit
    "ephios.core",
    "ephios.extra",
    "ephios.api",
    "django.contrib.admin",
    "django.contrib.auth",
    "polymorphic",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_filters",
    "guardian",
    "oauth2_provider",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "django_select2",
    "djangoformsetjs",
    "compressor",
    "recurrence",
    "statici18n",
    "dynamic_preferences.users.apps.UserPreferencesConfig",
    "crispy_forms",
    "crispy_bootstrap5",
    "webpush",
    "ephios.modellogging",
]

EPHIOS_APP_MODULES = [
    # core modules always receive plugin signals
    "ephios.core",
    "ephios.extra",
    "ephios.api",
]
CORE_PLUGINS = [
    "ephios.plugins.baseshiftstructures.apps.PluginApp",
    "ephios.plugins.basesignupflows.apps.PluginApp",
    "ephios.plugins.complexsignup.apps.PluginApp",
    "ephios.plugins.pages.apps.PluginApp",
    "ephios.plugins.qualification_management.apps.PluginApp",
    "ephios.plugins.guests.apps.PluginApp",
    "ephios.plugins.eventautoqualification.apps.PluginApp",
    "ephios.plugins.simpleresource.apps.PluginApp",
    "ephios.plugins.federation.apps.PluginApp",
    "ephios.plugins.files.apps.PluginApp",
]
PLUGINS = copy.copy(CORE_PLUGINS)
for ep in metadata.entry_points(group="ephios.plugins"):
    PLUGINS.append(ep.value)

INSTALLED_APPS += PLUGINS

INSTALLED_APPS += ["dynamic_preferences"]  # must come after our apps to collect preferences

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "ephios.extra.middleware.EphiosLocaleMiddleware",
    "ephios.extra.middleware.EphiosNotificationMiddleware",
    "ephios.core.services.files.EphiosMediaFileMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "ephios.modellogging.middleware.LoggingRequestMiddleware",
]

ROOT_URLCONF = "ephios.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "ephios/templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "dynamic_preferences.processors.global_preferences",
                "ephios.core.context.ephios_base_context",
            ],
            "debug": DEBUG,
        },
    },
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, "ephios/locale"),
]

WSGI_APPLICATION = "ephios.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {"default": env.db_url()}

# Caches
CACHES = {
    "default": {
        "TIMEOUT": 60 * 60 * 12,  # 12 hours
        **env.cache_url(default="locmemcache://"),
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
DJANGO_REDIS_IGNORE_EXCEPTIONS = True
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "ephios.core.services.password_reset.CustomMinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
    "ephios.extra.auth.EphiosOIDCAB",
]

AUTH_USER_MODEL = "core.UserProfile"
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/accounts/login/"
PASSWORD_RESET_TIMEOUT = 28 * 24 * 60 * 60  # seconds

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "de"
LANGUAGES = [
    ("de", gettext_lazy("German")),
    ("en", gettext_lazy("English")),
]

TIME_ZONE = "Europe/Berlin"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = env.str("STATIC_URL", default="/static/")
MEDIA_URL = env.str("MEDIA_URL", default="/usercontent/")
FALLBACK_MEDIA_SERVING = env.bool("FALLBACK_MEDIA_SERVING", default=DEBUG)

STATICFILES_DIRS = (os.path.join(BASE_DIR, "ephios/static"),)
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]
COMPRESS_ENABLED = not DEBUG
# https://www.accordbox.com/blog/how-use-scss-sass-your-django-project-python-way/
COMPRESS_PRECOMPILERS = (("text/x-scss", "django_libsass.SassCompiler"),)

# mail configuration
EMAIL_CONFIG = env.email_url("EMAIL_URL")
vars().update(EMAIL_CONFIG)
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")
SERVER_EMAIL = env.str("SERVER_EMAIL")
ADMINS = getaddresses([env("ADMINS")])

# logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "[%(levelname)s] %(asctime)s %(name)s :: %(message)s"},
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["require_debug_true"],
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "file": {
            "level": "DEBUG",
            "formatter": "default",
            "filters": [],
            **(
                {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "filename": os.path.join(LOG_DIR, "ephios.log"),
                    "when": "midnight",
                    "backupCount": env.int("LOGGING_BACKUP_DAYS", default=14),
                    "atTime": datetime.time(4),
                    "encoding": "utf-8",
                }
            ),
        },
    },
    "loggers": {
        "ephios": {
            "handlers": ["mail_admins", "console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "django": {
            "handlers": [],
            "level": "INFO",
            "propagate": True,
        },
        "django.server": {
            "handlers": [],
            "level": "INFO",
            "propagate": True,
        },
    },
    "root": {
        "handlers": ["mail_admins", "console", "file"],
        "level": "INFO",
    },
}


def GET_SITE_URL():
    site_url = env.str("SITE_URL")
    if site_url.endswith("/"):
        site_url = site_url[:-1]
    return site_url


def GET_USERCONTENT_URL():
    return MEDIA_URL


def GET_USERCONTENT_QUOTA():
    """Returns a tuple (used, free) of the user content quota in bytes"""
    used = sum(p.stat().st_size for p in Path(MEDIA_ROOT).rglob("*"))
    quota = env.int("MEDIA_FILES_DISK_QUOTA", default=0)
    disk_free = shutil.disk_usage(MEDIA_ROOT).free
    free = min(disk_free, quota * 1024 * 1024 - used) if quota else disk_free
    return used, free


# Guardian configuration
ANONYMOUS_USER_NAME = None
GUARDIAN_MONKEY_PATCH = False

# django-select2
# Prevent django-select from loading the select2 resources as we want to serve them locally
SELECT2_JS = ""
SELECT2_CSS = ""
SELECT2_I18N_PATH = ""
SELECT2_CACHE_BACKEND = "default"
SELECT2_THEME = "bootstrap-5"

# django-debug-toolbar
ENABLE_DEBUG_TOOLBAR = env.bool("DEBUG_TOOLBAR", False)
if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS.append("django_extensions")
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = env.list("INTERNAL_IPS", default=["127.0.0.1"])

# django-csp
# Bootstrap requires embedded SVG files loaded via a data URI. This is not ideal, but will only be fixed in
# bootstrap v5 or v6. See https://github.com/twbs/bootstrap/issues/25394 for details on the problem and
# https://security.stackexchange.com/a/167244 on why allowing data: is considered okay
CSP_IMG_SRC = ("'self'", "data:")
CSP_STYLE_SRC = "'self'"
CSP_INCLUDE_NONCE_IN = ["style-src"]

# django-crispy-forms
CRISPY_ALLOWED_TEMPLATE_PACKS = ("bootstrap5",)
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_FAIL_SILENTLY = not DEBUG

# django.contrib.messages
MESSAGE_TAGS = {
    constants.DEBUG: "alert-info",
    constants.INFO: "alert-info",
    constants.SUCCESS: "alert-success",
    constants.WARNING: "alert-warning",
    constants.ERROR: "alert-danger",
}

# PWA
PWA_APP_ICONS = [
    {
        "src": "/static/ephios/img/ephios-192x.png",
        "sizes": "192x192",
        "type": "image/png",
        "purpose": "maskable",
    },
    {
        "src": "/static/ephios/img/ephios-512x.png",
        "sizes": "512x512",
        "type": "image/png",
        "purpose": "maskable",
    },
    {
        "src": "/static/ephios/img/ephios-1024x.png",
        "sizes": "1024x1024",
        "type": "image/png",
        "purpose": "maskable",
    },
    {
        "src": "/static/ephios/img/ephios-symbol-red.svg",
        "sizes": "any",
        "type": "image/svg+xml",
        "purpose": "any",
    },
]

# django-webpush
VAPID_PRIVATE_KEY_PATH = env.str(
    "VAPID_PRIVATE_KEY_PATH", os.path.join(PRIVATE_DIR, "vapid_key.pem")
)
WEBPUSH_SETTINGS = {}
if os.path.exists(VAPID_PRIVATE_KEY_PATH):
    vp = Vapid().from_file(VAPID_PRIVATE_KEY_PATH)
    WEBPUSH_SETTINGS = {
        "VAPID_PUBLIC_KEY": b64urlencode(
            vp.public_key.public_bytes(
                serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
            )
        ),
        "VAPID_PRIVATE_KEY": vp,
        "VAPID_ADMIN_EMAIL": ADMINS[0][1],
    }


# Health check
# interval for calls to the run_periodic_tasks management command over which the cronjob is considered to be broken
RUN_PERIODIC_MAX_INTERVAL = 60 * 5 + 30  # 5 minutes + 30 seconds


# django-rest-framework
DEFAULT_LISTVIEW_PAGINATION = 100
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.DjangoObjectPermissions"],
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "ephios.api.access.auth.CustomOAuth2Authentication",
    ],
}

# drf-spectacular
SPECTACULAR_SETTINGS = {
    "TITLE": "ephios API",
    "DESCRIPTION": "ephios REST API",
    "VERSION": EPHIOS_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}

# Like UserProfile, these models are implemented using djangos private swappable API
# due to a shaky implementation in django-oauth-toolkit, we need to customize all models,
# although we only want to customize the AccessToken model
OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL = "api.AccessToken"
OAUTH2_PROVIDER_APPLICATION_MODEL = "api.Application"
OAUTH2_PROVIDER_ID_TOKEN_MODEL = "api.IDToken"
OAUTH2_PROVIDER_GRANT_MODEL = "api.Grant"
OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL = "api.RefreshToken"
OAUTH2_PROVIDER = {
    "SCOPES": {
        "PUBLIC_READ": gettext_lazy("Read public data like available events and shifts"),
        "PUBLIC_WRITE": gettext_lazy("Write public data like available events and shifts"),
        "ME_READ": gettext_lazy("Read own personal data and participations"),
        "ME_WRITE": gettext_lazy("Write own personal data and participations"),
        "CONFIDENTIAL_READ": gettext_lazy(
            "Read confidential data like all users profile and participations"
        ),
        "CONFIDENTIAL_WRITE": gettext_lazy(
            "Write confidential data like all users profile and participations"
        ),
    },
    "REFRESH_TOKEN_EXPIRE_SECONDS": timedelta(days=90),
}

# SECURITY SETTINGS
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = True
    SECURE_REFERRER_POLICY = "same-origin"
    # 1 day by default, change to 1 year in production (see deployment docs)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600 * 24)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
    CONN_MAX_AGE = env.int("CONN_MAX_AGE", default=0)

if env.bool("TRUST_X_FORWARDED_PROTO", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Transitional/deprecated settings
FORMS_URLFIELD_ASSUME_HTTPS = (
    True  # https://docs.djangoproject.com/en/5.1/ref/settings/#forms-urlfield-assume-https
)
