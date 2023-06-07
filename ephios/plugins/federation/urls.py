from django.urls import path

from ephios.plugins.federation.views import SharedEventListView

app_name = "federation"
urlpatterns = [
    path("api/federation/events", SharedEventListView.as_view()),
]
