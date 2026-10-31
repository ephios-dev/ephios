from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.eventlistquickfilters.models import EventListQuickFilter


class EventListQuickFilterListView(CustomPermissionRequiredMixin, ListView):
    permission_required = "core.change_eventtype"
    model = EventListQuickFilter
    ordering = ("position", "label")

    def get_queryset(self):
        return super().get_queryset().prefetch_related("filter_types")


class EventListQuickFilterCreateView(CustomPermissionRequiredMixin, CreateView):
    permission_required = "core.add_eventtype"
    accept_object_perms = False
    model = EventListQuickFilter
    fields = ["label", "filter_types", "visible_for_groups", "default_for_groups", "position"]
    success_url = reverse_lazy("eventlistquickfilters:eventlistquickfilter_list")


class EventListQuickFilterUpdateView(CustomPermissionRequiredMixin, UpdateView):
    permission_required = "core.change_eventtype"
    model = EventListQuickFilter
    fields = ["label", "filter_types", "visible_for_groups", "default_for_groups", "position"]
    success_url = reverse_lazy("eventlistquickfilters:eventlistquickfilter_list")


class EventListQuickFilterDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "core.delete_eventtype"
    model = EventListQuickFilter
    success_url = reverse_lazy("eventlistquickfilters:eventlistquickfilter_list")
