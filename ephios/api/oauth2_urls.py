from django.urls import re_path
from oauth2_provider import views
from oauth2_provider.urls import base_urlpatterns

from ephios.extra.permissions import staff_required

app_name = "oauth2_provider"


management_urlpatterns = [
    # Application management views
    re_path(r"^applications/$", staff_required(views.ApplicationList.as_view()), name="list"),
    re_path(
        r"^applications/register/$",
        staff_required(views.ApplicationRegistration.as_view()),
        name="register",
    ),
    re_path(
        r"^applications/(?P<pk>[\w-]+)/$",
        staff_required(views.ApplicationDetail.as_view()),
        name="detail",
    ),
    re_path(
        r"^applications/(?P<pk>[\w-]+)/delete/$",
        staff_required(views.ApplicationDelete.as_view()),
        name="delete",
    ),
    re_path(
        r"^applications/(?P<pk>[\w-]+)/update/$",
        staff_required(views.ApplicationUpdate.as_view()),
        name="update",
    ),
    # Token management views
    re_path(
        r"^authorized_tokens/$",
        views.AuthorizedTokensListView.as_view(),
        name="authorized-token-list",
    ),
    re_path(
        r"^authorized_tokens/(?P<pk>[\w-]+)/delete/$",
        views.AuthorizedTokenDeleteView.as_view(),
        name="authorized-token-delete",
    ),
]

urlpatterns = base_urlpatterns + management_urlpatterns
