from django.urls import path

from ephios.plugins.simpleresource.views import ResourceCategoryListView

app_name = "simpleresource"
urlpatterns = [
    path(
        "resource_management/categories/",
        ResourceCategoryListView.as_view(),
        name="resourcecategory_list",
    ),
]
