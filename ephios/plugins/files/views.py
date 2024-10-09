from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from guardian.mixins import LoginRequiredMixin

from ephios.extra.mixins import CustomPermissionRequiredMixin, MediaViewMixin
from ephios.extra.utils import accelerated_media_response
from ephios.plugins.files.forms import DocumentForm
from ephios.plugins.files.models import Document


class DocumentView(LoginRequiredMixin, MediaViewMixin, DetailView):
    model = Document

    def get(self, request, *args, **kwargs):
        return accelerated_media_response(self.get_object().file)


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
