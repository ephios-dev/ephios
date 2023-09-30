from django.conf import settings


class EphiosLocaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.LANGUAGE_COOKIE_NAME not in request.COOKIES:
            try:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, request.user.preferred_language)
            except (KeyError, AttributeError):
                pass
        return response
