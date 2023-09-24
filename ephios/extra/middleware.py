from django.conf import settings
from django.middleware.locale import LocaleMiddleware


class EphiosLocaleMiddleware(LocaleMiddleware):
    def process_response(self, request, response):
        response = super().process_response(request, response)
        if settings.LANGUAGE_COOKIE_NAME not in request.COOKIES:
            try:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, request.user.language)
            except (KeyError, AttributeError):
                pass
        return response
