from django.urls import reverse
from django.views.generic import FormView, ListView

from ephios.core.models import Qualification
from ephios.core.views.settings import SettingsViewMixin
from ephios.extra.mixins import StaffRequiredMixin

# Templates in this plugin are under core/, because Qualification is a core model.
from ephios.plugins.qualification_management.importing import QualificationImportForm


class QualificationListView(StaffRequiredMixin, SettingsViewMixin, ListView):
    model = Qualification
    ordering = ("category__title", "title")


class QualificationImportView(StaffRequiredMixin, SettingsViewMixin, FormView):
    template_name = "core/import.html"
    form_class = QualificationImportForm

    def get_success_url(self):
        return reverse("qualification_management:settings_qualification_list")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class PageCreateView(StaffRequiredMixin, SettingsViewMixin, CreateView):
    model = Qualification
    fields = ["title", "content", "slug", "show_in_footer", "publicly_visible"]

    def get_success_url(self):
        messages.success(self.request, _("Page saved successfully."))
        return reverse("pages:settings_page_list")


class PageEditView(StaffRequiredMixin, SettingsViewMixin, UpdateView):
    model = Page
    fields = ["title", "content", "slug", "show_in_footer", "publicly_visible"]

    def get_success_url(self):
        messages.success(self.request, _("Page saved successfully."))
        return reverse("pages:settings_page_list")


class PageDeleteView(StaffRequiredMixin, SettingsViewMixin, DeleteView):
    model = Page

    def get_success_url(self):
        messages.info(self.request, _("Page deleted successfully."))
        return reverse("pages:settings_page_list")
