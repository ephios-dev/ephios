from django.urls import path

from service_management import views

app_name = "service_management"
urlpatterns = [
    path("", views.ListView.as_view(), name="service_list"),
    # path("<int:pk>/edit", views.UpdateView.as_view(), name="service_change"),
    # path("<int:pk>/delete", views.DeleteView.as_view(), name="service_delete"),
    path("<int:pk>/", views.DetailView.as_view(), name="service_detail"),
    # path("add/", views.CreateView.as_view(), name="service_add"),
]
