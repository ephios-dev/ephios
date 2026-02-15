from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, FormView, ListView, UpdateView

from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.simpleresource.forms import ResourceCategoryFormset
from ephios.plugins.simpleresource.models import Resource, ResourceCategory


class ResourceListView(CustomPermissionRequiredMixin, ListView):
    permission_required = "simpleresource.view_resourcecategory"
    model = Resource
    ordering = ("category__name", "title")

    def get_queryset(self):
        return super().get_queryset().select_related("category")


class ResourceCreateView(CustomPermissionRequiredMixin, CreateView):
    permission_required = "simpleresource.add_resource"
    accept_object_perms = False
    model = Resource
    fields = ["title", "category"]
    success_url = reverse_lazy("simpleresource:resource_list")


class ResourceUpdateView(CustomPermissionRequiredMixin, UpdateView):
    permission_required = "simpleresource.change_resource"
    model = Resource
    fields = ("title", "category")
    success_url = reverse_lazy("simpleresource:resource_list")


class ResourceDeleteView(CustomPermissionRequiredMixin, DeleteView):
    permission_required = "simpleresource.delete_resource"
    model = Resource
    success_url = reverse_lazy("simpleresource:resource_list")


class ResourceCategorySetUpdateView(CustomPermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = ResourceCategoryFormset
    template_name = "simpleresource/resourcecategories_form.html"
    permission_required = "simpleresource.add_resource"
    success_url = reverse_lazy("simpleresource:resource_list")
    success_message = _("Resource categories updated successfully.")

    def get_form_kwargs(self):
        return {"queryset": ResourceCategory.objects.all(), **super().get_form_kwargs()}

    def form_valid(self, form):
        with transaction.atomic():
            form.save()
        return super().form_valid(form)
