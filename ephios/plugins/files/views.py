from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from guardian.mixins import LoginRequiredMixin

from ephios.extra.mixins import CustomPermissionRequiredMixin, MediaViewMixin
from ephios.extra.utils import accelerated_media_response
from ephios.plugins.files.forms import DocumentForm
from ephios.plugins.files.models import Document, DownloadTicket


class DownloadTicketView(MediaViewMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            ticket = DownloadTicket.objects.get(
                token=self.kwargs["token"], expiration__gte=timezone.now()
            )
            file = ticket.document.file
            ticket.delete()
            return accelerated_media_response(file)
        except DownloadTicket.DoesNotExist:
            raise Http404()


class DocumentView(LoginRequiredMixin, DetailView):
    model = Document

    def get(self, request, *args, **kwargs):
        ticket = DownloadTicket.objects.create(document=self.get_object())
        return redirect(reverse("files:document_ticket", kwargs={"token": ticket.token}))


class DocumentListView(CustomPermissionRequiredMixin, ListView):
    model = Document
    permission_required = "files.add_document"

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        used, free = settings.GET_USERCONTENT_QUOTA()
        context["quota_free"] = free
        context["quota_used"] = used
        return context


class DocumentCreateView(CustomPermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Document
    permission_required = "files.add_document"
    form_class = DocumentForm
    success_url = reverse_lazy("files:settings_document_list")
    success_message = _("File saved successfully.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class DocumentUpdateView(CustomPermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Document
    permission_required = "files.change_document"
    form_class = DocumentForm
    success_url = reverse_lazy("files:settings_document_list")
    success_message = _("File saved successfully.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class DocumentDeleteView(CustomPermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Document
    permission_required = "files.delete_document"
    success_url = reverse_lazy("files:settings_document_list")
    success_message = _("File deleted successfully.")
