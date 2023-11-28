from django.views.generic import DetailView, ListView
from guardian.mixins import LoginRequiredMixin

from ephios.core.models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    ordering = "-created_at"

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationDetailView(DetailView):
    model = Notification

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
