from django.contrib import messages
from django.db.models import Max
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.eventlistquickfilters.forms import EventListQuickFilterForm
from ephios.plugins.eventlistquickfilters.models import EventListQuickFilter


class EventListQuickFilterListView(CustomPermissionRequiredMixin, ListView):
    permission_required = "core.change_eventtype"
    model = EventListQuickFilter
    ordering = ("position", "label")

    def get_queryset(self):
        return super().get_queryset().prefetch_related("filter_types").order_by("position", "id")


class EventListQuickFilterCreateView(CustomPermissionRequiredMixin, CreateView):
    permission_required = "core.add_eventtype"
    accept_object_perms = False
    model = EventListQuickFilter
    form_class = EventListQuickFilterForm
    template_name = "core/settings/settings_base_form.html"
    settings_list_url = reverse_lazy("eventlistquickfilters:eventlistquickfilter_list")
    success_url = reverse_lazy("eventlistquickfilters:eventlistquickfilter_list")

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault(
            "position",
            EventListQuickFilter.objects.aggregate(max_position=Max("position", default=0))[
                "max_position"
            ]
            + 1,
        )
        return initial

    def get_success_url(self):
        messages.success(self.request, _("Event list quick filter saved successfully."))
        return reverse("eventlistquickfilters:eventlistquickfilter_list")


class EventListQuickFilterUpdateView(CustomPermissionRequiredMixin, UpdateView):
    permission_required = "core.change_eventtype"
    model = EventListQuickFilter
    form_class = EventListQuickFilterForm
    template_name = "core/settings/settings_base_form.html"
    settings_list_url = reverse_lazy("eventlistquickfilters:eventlistquickfilter_list")
    success_url = reverse_lazy("eventlistquickfilters:eventlistquickfilter_list")

    def get_success_url(self):
        messages.success(self.request, _("Event list quick filter saved successfully."))
        return reverse("eventlistquickfilters:eventlistquickfilter_list")


class EventListQuickFilterDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "core.delete_eventtype"
    model = EventListQuickFilter
    template_name = "core/settings/settings_base_confirm_delete.html"
    settings_list_url = reverse_lazy("eventlistquickfilters:eventlistquickfilter_list")

    def get_success_url(self):
        messages.info(self.request, _("Event list quick filter deleted successfully."))
        return reverse("eventlistquickfilters:eventlistquickfilter_list")
