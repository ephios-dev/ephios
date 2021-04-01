import copy
import os
from email.utils import getaddresses

try:
    import importlib_metadata  # importlib is broken on python3.8, using backport
except ImportError:
    import importlib.metadata as importlib_metadata

import environ
from cryptography.hazmat.primitives import serialization
from django.contrib.messages import constants
from py_vapid import Vapid, b64urlencode

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env = environ.Env()
# for syntax see https://django-environ.readthedocs.io/en/latest/
environ.Env.read_env(env_file=os.path.join(BASE_DIR, ".env"))

DATA_DIR = env.str("DATA_DIR", default=os.path.join(BASE_DIR, "data"))
if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)

SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
SITE_URL = env.str("SITE_URL")
if SITE_URL.endswith("/"):
    SITE_URL = SITE_URL[:-1]

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_REFERRER_POLICY = "same-origin"

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "polymorphic",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "guardian",
    "django_select2",
    "djangoformsetjs",
    "compressor",
    "recurrence",
    "statici18n",
    "dynamic_preferences.users.apps.UserPreferencesConfig",
    "crispy_forms",
    "webpush",
    "ephios.modellogging",
]

EPHIOS_CORE_MODULES = [
    "ephios.core",
    "ephios.extra",
]
INSTALLED_APPS += EPHIOS_CORE_MODULES

CORE_PLUGINS = [
    "ephios.plugins.basesignup",
    "ephios.plugins.pages",
    "ephios.plugins.guests",
    "ephios.plugins.eventautoqualification",
]
PLUGINS = copy.copy(CORE_PLUGINS)
for ep in importlib_metadata.entry_points().get("ephios.plugins", []):
    PLUGINS.append(ep.module)

INSTALLED_APPS += PLUGINS

INSTALLED_APPS += ["dynamic_preferences"]  # must come after our apps to collect preferences

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
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
        },
    },
]

LOCALE_PATHS = (os.path.join(BASE_DIR, "ephios/locale"),)

WSGI_APPLICATION = "ephios.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {"default": env.db_url()}

# Caches
CACHES = {"default": env.cache_url(default="locmemcache://")}
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

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)

AUTH_USER_MODEL = "core.UserProfile"
LOGIN_REDIRECT_URL = "/"
PASSWORD_RESET_TIMEOUT = 28 * 24 * 60 * 60  # seconds

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "de"

TIME_ZONE = "Europe/Berlin"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = env.str("STATIC_URL")
STATIC_ROOT = env.str("STATIC_ROOT")
STATICFILES_DIRS = (os.path.join(BASE_DIR, "ephios/static"),)
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
)
COMPRESS_ENABLED = not DEBUG

# mail configuration
EMAIL_CONFIG = env.email_url("EMAIL_URL")
vars().update(EMAIL_CONFIG)
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")
SERVER_EMAIL = env.str("SERVER_EMAIL")
ADMINS = getaddresses([env("ADMINS")])

# logging
if not DEBUG:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": True,
        "handlers": {
            "mail_admins": {"level": "ERROR", "class": "django.utils.log.AdminEmailHandler"}
        },
        "loggers": {
            "django": {
                "handlers": ["mail_admins"],
                "level": "ERROR",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
        },
    }


# Guardian configuration
ANONYMOUS_USER_NAME = None
GUARDIAN_MONKEY_PATCH = False

# django-select2
# Prevent django-select from loading the select2 resources as we want to serve them locally
SELECT2_JS = ""
SELECT2_CSS = ""
SELECT2_I18N_PATH = ""

# django-debug-toolbar
if DEBUG:
    INSTALLED_APPS.append("django_extensions")
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = env.str("INTERNAL_IPS")

# django-csp
# Bootstrap requires embedded SVG files loaded via a data URI. This is not ideal, but will only be fixed in
# bootstrap v5 or v6. See https://github.com/twbs/bootstrap/issues/25394 for details on the problem and
# https://security.stackexchange.com/a/167244 on why allowing data: is considered okay
CSP_IMG_SRC = ("'self'", "data:")
CSP_STYLE_SRC = ("'self'",)
CSP_INCLUDE_NONCE_IN = ["style-src"]

# django-crispy-forms
CRISPY_TEMPLATE_PACK = "bootstrap4"
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
    {"src": "/static/ephios/img/ephios-192x.png", "sizes": "192x192", "purpose": "any maskable"},
    {"src": "/static/ephios/img/ephios-512x.png", "sizes": "512x512", "purpose": "any maskable"},
    {"src": "/static/ephios/img/ephios-1024x.png", "sizes": "1024x1024", "purpose": "any maskable"},
]

# django-webpush
if vapid_private_key_path := env.str("VAPID_PRIVATE_KEY_PATH", None):
    vp = Vapid().from_file(vapid_private_key_path)
    WEBPUSH_SETTINGS = {
        "VAPID_PUBLIC_KEY": b64urlencode(
            vp.public_key.public_bytes(
                serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
            )
        ),
        "VAPID_PRIVATE_KEY": vp,
        "VAPID_ADMIN_EMAIL": ADMINS[0][1],
    }
