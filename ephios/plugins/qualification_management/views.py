from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, FormView, ListView, UpdateView
from django_select2.forms import Select2MultipleWidget

from ephios.core.models import Qualification
from ephios.core.views.settings import SettingsViewMixin
from ephios.extra.mixins import StaffRequiredMixin

# Templates in this plugin are under core/, because Qualification is a core model.
from ephios.plugins.qualification_management.importing import (
    QualificationChangeManager,
    QualificationImportForm,
)


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


class QualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = ["title", "uuid", "abbreviation", "category", "included_qualifications"]
        widgets = {"included_qualifications": Select2MultipleWidget}
        help_texts = {
            "uuid": _(
                "Used to identify qualifications accross the ephios ecosystem. Only change if you know what you are doing."
            )
        }


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


class QualificationDeleteView(StaffRequiredMixin, SettingsViewMixin, DeleteView):
    model = Qualification

    # TODO ask whether to fix inclusion graph and then implement that

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        # instead of plain `self.object.delete()`, we are graceful about qualification inclusions
        manager = QualificationChangeManager()
        manager.remove_qualifications_from_db_fixing_inclusion(self.object)
        manager.commit()

        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        messages.info(self.request, _("Qualification was deleted."))
        return reverse("qualification_management:settings_qualification_list")
