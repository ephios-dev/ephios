from oauth2_provider.urls import base_urlpatterns

app_name = "oauth2_provider"

management_urlpatterns = [
    # views to manage oauth2 applications are part of the API django app url config under the "API" namespace
]

urlpatterns = base_urlpatterns + management_urlpatterns
