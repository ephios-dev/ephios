from django.conf import settings

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
        response = self.get_response(request)
        if getattr(request.user, "is_authenticated", False) and (
            notification_id := request.GET.get(NOTIFICATION_READ_PARAM_NAME)
        ):
            from ephios.core.models import Notification

            try:
                notification = Notification.objects.get(
                    pk=notification_id,
                    user=request.user,
                    read=False,
                )
            except (Notification.DoesNotExist, ValueError):
                # ValueError if `notification_id` is not an integer
                pass
            else:
                notification.read = True
                notification.save(update_fields=["read"])
        return response
