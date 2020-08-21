from django.urls import path

from event_management import views

app_name = "event_management"
urlpatterns = [
    path("", views.HomeView.as_view(), name="index"),
    path("events/", views.EventListView.as_view(), name="event_list"),
    # path("<int:pk>/edit", views.UpdateView.as_view(), name="event_change"),
    # path("<int:pk>/delete", views.DeleteView.as_view(), name="event_delete"),
    path("events/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("events/create/", views.EventCreateView.as_view(), name="event_create"),
    path("shifts/<int:pk>/register", views.ShiftRegisterView.as_view(), name="shift_register",),
]
