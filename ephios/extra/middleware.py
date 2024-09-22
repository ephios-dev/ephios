from urllib.parse import urljoin, urlsplit

from django.conf import settings
from django.shortcuts import redirect

from ephios.core.services.notifications.types import NOTIFICATION_READ_PARAM_NAME


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


class EphiosNotificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from ephios.core.models import Notification

        response = self.get_response(request)
        if NOTIFICATION_READ_PARAM_NAME in request.GET:
            try:
                notification = Notification.objects.get(
                    pk=request.GET[NOTIFICATION_READ_PARAM_NAME]
                )
                if notification.user == request.user and not notification.read:
                    notification.read = True
                    notification.save()
            except Notification.DoesNotExist:
                pass
        return response


class EphiosMediaFileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.get_host() == urlsplit(settings.GET_USERCONTENT_URL()).netloc
            and request.resolver_match.url_name != "document"
        ):
            return redirect(urljoin(settings.GET_SITE_URL(), request.path))
        return response
