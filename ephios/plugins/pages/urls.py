from django.urls import path

from ephios.plugins.pages.views import PageView

urlpatterns = [
    path("page/<slug:slug>/", PageView.as_view(), name="view_page"),
]
