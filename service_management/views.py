from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView, DeleteView

from service_management.models import Service


class ListView(LoginRequiredMixin, ListView):
    model = Service


class DetailView(LoginRequiredMixin, DetailView):
    model = Service


class UpdateView(LoginRequiredMixin, UpdateView):
    model = Service


class DeleteView(LoginRequiredMixin, DeleteView):
    model = Service
