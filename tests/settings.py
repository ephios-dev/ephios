from ephios.settings import *  # no-qa

LANGUAGE_CODE = "en"

DYNAMIC_PREFERENCES = {
    # the cache is not invalidated between tests, so tests aren't isolated properly with the cache enabled
    "ENABLE_CACHE": False,
}
