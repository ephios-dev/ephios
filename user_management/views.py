from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView


class ProfileView(LoginRequiredMixin, DetailView):
    def get_object(self, queryset=None):
        return self.request.user
