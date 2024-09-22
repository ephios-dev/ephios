import os
from urllib.parse import urlsplit

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from guardian.mixins import LoginRequiredMixin

from ephios.plugins.files.models import Document


class DocumentView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if (loc := urlsplit(settings.GET_USERCONTENT_URL()).netloc) and request.get_host() != loc:
            return redirect(settings.GET_USERCONTENT_URL() + request.path)
        document = get_object_or_404(Document, id=kwargs["pk"])
        if settings.FALLBACK_MEDIA_SERVING:
            response = FileResponse(document.file)
        else:
            response = HttpResponse()
            response["X-Accel-Redirect"] = document.file.url
        response["Content-Disposition"] = (
            "attachment; filename=" + os.path.split(document.file.name)[1]
        )
        return response
