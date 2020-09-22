from django.urls import path

from ephios.plugins.basesignup.signup.confirm import RequestConfirmDispositionView

app_name = "plugins"
urlpatterns = [
    path("pages/<slug:slug>/", PagesView.as_view(), name="pages:view_page",),
]
