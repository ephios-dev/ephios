import os
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from guardian.mixins import LoginRequiredMixin

from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.files.forms import DocumentForm
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


class DocumentListView(CustomPermissionRequiredMixin, ListView):
    model = Document
    permission_required = "files.add_document"


class DocumentCreateView(CustomPermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Document
    permission_required = "files.add_document"
    form_class = DocumentForm
    success_url = reverse_lazy("files:settings_document_list")
    success_message = _("File saved successfully.")


class DocumentUpdateView(CustomPermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Document
    permission_required = "files.change_document"
    form_class = DocumentForm
    success_url = reverse_lazy("files:settings_document_list")
    success_message = _("File saved successfully.")


class DocumentDeleteView(CustomPermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Document
    permission_required = "files.delete_document"
    success_url = reverse_lazy("files:settings_document_list")
    success_message = _("File deleted successfully.")
