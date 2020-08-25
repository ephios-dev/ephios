from django.urls import path

from event_management import views
from event_management.views import ShiftConfigurationFormView

app_name = "event_management"
urlpatterns = [
    path("", views.HomeView.as_view(), name="index"),
    path("events/", views.EventListView.as_view(), name="event_list"),
    # path("<int:pk>/edit", views.UpdateView.as_view(), name="event_change"),
    path("events/<int:pk>/delete", views.EventDeleteView.as_view(), name="event_delete"),
    path("events/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("events/<int:pk>/createshift", views.ShiftCreateView.as_view(), name="event_createshift"),
    path("events/<int:pk>/activate", views.EventActivateView.as_view(), name="event_activate"),
    path("events/create/", views.EventCreateView.as_view(), name="event_create"),
    path("shifts/<int:pk>/register", views.ShiftRegisterView.as_view(), name="shift_register",),
    path(
        "signup_methods/<slug:slug>/configuration_form",
        ShiftConfigurationFormView.as_view(),
        name="signupmethod_configurationform",
    ),
]
