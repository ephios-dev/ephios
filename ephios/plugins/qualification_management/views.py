from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, FormView, ListView, UpdateView

from ephios.core.models import Qualification, QualificationCategory
from ephios.core.views.settings import SettingsViewMixin
from ephios.extra.mixins import StaffRequiredMixin
from ephios.plugins.qualification_management.forms import (
    QualificationCategoryFormset,
    QualificationDeleteForm,
    QualificationForm,
    QualificationImportForm,
)

# Templates in this plugin are under core/, because Qualification is a core model.


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


class QualificationCreateView(StaffRequiredMixin, SettingsViewMixin, CreateView):
    model = Qualification
    form_class = QualificationForm

    def get_success_url(self):
        messages.success(self.request, _("Qualification was saved."))
        return reverse("qualification_management:settings_qualification_list")


class QualificationUpdateView(StaffRequiredMixin, SettingsViewMixin, UpdateView):
    model = Qualification
    form_class = QualificationForm

    def get_success_url(self):
        messages.success(self.request, _("Qualification was saved."))
        return reverse("qualification_management:settings_qualification_list")


class QualificationDeleteView(StaffRequiredMixin, SettingsViewMixin, UpdateView):
    model = Qualification
    form_class = QualificationDeleteForm
    template_name_suffix = "_confirm_delete"

    def get_success_url(self):
        messages.info(self.request, _("Qualification was deleted."))
        return reverse("qualification_management:settings_qualification_list")


class QualificationCategorySetUpdateView(StaffRequiredMixin, SettingsViewMixin, FormView):
    form_class = QualificationCategoryFormset
    template_name = "core/qualificationcategories_form.html"

    def get_form_kwargs(self):
        return {"queryset": QualificationCategory.objects.all(), **super().get_form_kwargs()}

    def form_valid(self, form):
        with transaction.atomic():
            form.save()
        return super().form_valid(form)

    def get_success_url(self):
        messages.info(self.request, _("Qualification categories saved."))
        return reverse("qualification_management:settings_qualification_list")
