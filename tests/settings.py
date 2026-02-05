import os

from ephios.settings import *  # noqa

LANGUAGE_CODE = "en"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

DEFAULT_SITE_URL = "http://localhost:8000"
