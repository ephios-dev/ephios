from ephios.settings import *  # no-qa

LANGUAGE_CODE = "en"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def GET_SITE_URL():
    return "http://localhost:8000"
