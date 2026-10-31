from django.urls import path

from ephios.plugins.eventlistquickfilters.views import (
    EventListQuickFilterCreateView,
    EventListQuickFilterDeleteView,
    EventListQuickFilterListView,
    EventListQuickFilterUpdateView,
)

app_name = "eventlistquickfilters"
urlpatterns = [
    path(
        "eventlistquickfilters/",
        EventListQuickFilterListView.as_view(),
        name="eventlistquickfilter_list",
    ),
    path(
        "eventlistquickfilters/add/",
        EventListQuickFilterCreateView.as_view(),
        name="eventlistquickfilter_add",
    ),
    path(
        "eventlistquickfilters/<int:pk>/edit/",
        EventListQuickFilterUpdateView.as_view(),
        name="eventlistquickfilter_edit",
    ),
    path(
        "eventlistquickfilters/<int:pk>/delete/",
        EventListQuickFilterDeleteView.as_view(),
        name="eventlistquickfilter_delete",
    ),
]
