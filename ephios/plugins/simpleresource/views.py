from django.views.generic import ListView

from ephios.extra.mixins import CustomPermissionRequiredMixin
from ephios.plugins.simpleresource.models import Resource, ResourceCategory


class ResourceCategoryListView(CustomPermissionRequiredMixin, ListView):
    model = ResourceCategory
    permission_required = "simpleresource.view_resourcecategory"


class ResourceListView(CustomPermissionRequiredMixin, ListView):
    model = Resource
    permission_required = "simpleresource.view_resource"
