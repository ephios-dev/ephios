from django.urls import path

from ephios.plugins.files.views import DocumentView

app_name = "files"
urlpatterns = [
    path("documents/<int:pk>/", DocumentView.as_view(), name="document"),
]
