from contextlib import contextmanager

from django.conf import settings
from django.utils import translation


@contextmanager
def language(lang):
    previous_language = translation.get_language()
    lang = lang or settings.LANGUAGE_CODE
    translation.activate(lang)
    try:
        yield
    finally:
        translation.activate(previous_language)
