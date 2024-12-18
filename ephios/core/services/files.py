import os
import random
import string
from urllib.parse import urljoin, urlsplit, urlunsplit

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View


class UserContentView(View):
    """
    Use this on views that serve user content/media files.
    """

    is_usercontent_view = True

    def dispatch(self, request, *args, **kwargs):
        # If media files are served from a different domain and
        # the user requests media files from the app domain via this view --> 404
        if (loc := urlsplit(settings.GET_USERCONTENT_URL()).netloc) and request.get_host() != loc:
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)


class FileTicketView(UserContentView):
    """
    Deliver user content identified by a short-lived secret.
    """

    def get(self, request, *args, **kwargs):
        file = cache.get(self.kwargs["ticket"])
        if file is None:
            raise Http404()
        return accelerated_media_response(file)


def accelerated_media_response(file):
    if settings.FALLBACK_MEDIA_SERVING:
        # use built-in django file serving - only as a fallback as this is slow
        response = FileResponse(file)
    else:
        # use nginx x-accel-redirect for faster file serving
        # nginx needs to be set up to serve files from the media url
        response = HttpResponse()
        response["X-Accel-Redirect"] = file.url
    response["Content-Disposition"] = "attachment; filename=" + os.path.split(file.name)[1]
    return response


def file_ticket(file):
    key = "".join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(32)
    )
    cache.set(key, file, 60)
    return key


def redirect_to_file_download(field_file):
    """
    Shortcut for redirecting to the ticketed media file download view.
    """
    if loc := urlsplit(settings.GET_USERCONTENT_URL()).netloc:
        ticket = file_ticket(field_file)
        path = reverse("core:file_ticket", kwargs={"ticket": ticket})
        return redirect(urlunsplit(("http" if settings.DEBUG else "https", loc, path, "", "")))
    return accelerated_media_response(field_file)


class EphiosMediaFileMiddleware:
    """Ensure only media files are served from the media domain."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            # if the usercontent URL does not contain a domain, the request host will be checked against `None` --> no redirect loop
            request.get_host() == urlsplit(settings.GET_USERCONTENT_URL()).netloc
            and request.resolver_match
            and not getattr(request.resolver_match.func.view_class, "is_usercontent_view", False)
        ):
            return redirect(urljoin(settings.GET_SITE_URL(), request.path))
        return response
