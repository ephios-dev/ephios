from django.urls import path

from event_management import views

app_name = "event_management"
urlpatterns = [
    path("", views.HomeView.as_view(), name="index"),
    path("services/", views.ListView.as_view(), name="service_list"),
    # path("<int:pk>/edit", views.UpdateView.as_view(), name="service_change"),
    # path("<int:pk>/delete", views.DeleteView.as_view(), name="service_delete"),
    path("services/<int:pk>/", views.DetailView.as_view(), name="service_detail"),
    # path("add/", views.CreateView.as_view(), name="service_add"),
    path(
        "shifts/<int:pk>/register",
        views.ShiftRegisterView.as_view(),
        name="shift_register",
    ),
]
