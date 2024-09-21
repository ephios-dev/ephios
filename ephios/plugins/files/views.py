import os

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from guardian.mixins import LoginRequiredMixin

from ephios.plugins.files.models import Document


class DocumentView(View, LoginRequiredMixin):
    def get(self, request, *args, **kwargs):
        document = get_object_or_404(Document, id=kwargs["pk"])
        response = HttpResponse()
        response["Content-Disposition"] = (
            "attachment; filename=" + os.path.split(document.file.name)[1]
        )
        response["X-Accel-Redirect"] = settings.MEDIA_URL + document.file.name
        return response
