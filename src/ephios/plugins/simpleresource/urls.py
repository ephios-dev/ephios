from django.urls import path

from ephios.plugins.simpleresource.views import (
    ResourceCategorySetUpdateView,
    ResourceCreateView,
    ResourceDeleteView,
    ResourceListView,
    ResourceUpdateView,
)

app_name = "simpleresource"
urlpatterns = [
    path(
        "resources/",
        ResourceListView.as_view(),
        name="resource_list",
    ),
    path(
        "resources/add/",
        ResourceCreateView.as_view(),
        name="resource_add",
    ),
    path(
        "resources/<int:pk>/edit/",
        ResourceUpdateView.as_view(),
        name="resource_edit",
    ),
    path(
        "resources/<int:pk>/delete/",
        ResourceDeleteView.as_view(),
        name="resource_delete",
    ),
    path(
        "resources/categories/", ResourceCategorySetUpdateView.as_view(), name="resource_categories"
    ),
]
