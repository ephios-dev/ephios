from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.simpleresource.models import Resource


class ResourceListView(CustomPermissionRequiredMixin, ListView):
    permission_required = "simpleresource.view_resourcecategory"
    model = Resource
    ordering = ("category__name", "title")

    def get_queryset(self):
        return super().get_queryset().select_related("category")


class ResourceCreateView(CustomPermissionRequiredMixin, CreateView):
    permission_required = "simpleresource.add_resource"
    model = Resource
    fields = ["title", "category"]
    success_url = reverse_lazy("simpleresource:resource_list")


class ResourceUpdateView(CustomPermissionRequiredMixin, UpdateView):
    permission_required = "simpleresource.change_resourcecategory"
    model = Resource
    fields = ("title", "category")
    success_url = reverse_lazy("simpleresource:resource_list")


class ResourceDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "simpleresource.delete_resourcecategory"
    model = Resource
    success_url = reverse_lazy("simpleresource:resource_list")
