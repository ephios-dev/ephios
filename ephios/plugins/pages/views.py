from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.pages.models import Page


class PageListView(CustomPermissionRequiredMixin, ListView):
    model = Page
    permission_required = "pages.add_page"


class PageView(DetailView):
    model = Page

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = self.get_object()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated and not self.object.publicly_visible:
            return redirect_to_login(self.request.get_full_path())
        return super().dispatch(request, *args, **kwargs)


class PageCreateView(CustomPermissionRequiredMixin, CreateView):
    model = Page
    permission_required = "pages.add_page"
    accept_object_perms = False
    fields = ["title", "slug", "content", "show_in_footer", "publicly_visible"]

    def get_success_url(self):
        messages.success(self.request, _("Page saved successfully."))
        return reverse("pages:settings_page_list")


class PageUpdateView(CustomPermissionRequiredMixin, UpdateView):
    model = Page
    permission_required = "pages.change_page"
    fields = ["title", "slug", "content", "show_in_footer", "publicly_visible"]

    def get_success_url(self):
        messages.success(self.request, _("Page saved successfully."))
        return reverse("pages:settings_page_list")


class PageDeleteView(CustomPermissionRequiredMixin, DeleteView):
    model = Page
    permission_required = "pages.delete_page"

    def get_success_url(self):
        messages.info(self.request, _("Page deleted successfully."))
        return reverse("pages:settings_page_list")
