from django.urls import reverse
from django.views.generic import DetailView, ListView, RedirectView
from django.views.generic.detail import SingleObjectMixin
from guardian.mixins import LoginRequiredMixin

from ephios.core.models import Notification


class OwnNotificationMixin(LoginRequiredMixin):
    model = Notification

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")


class NotificationListView(OwnNotificationMixin, ListView):
    paginate_by = 20


class NotificationDetailView(OwnNotificationMixin, DetailView):
    pass


class NotificationMarkAsReadView(OwnNotificationMixin, SingleObjectMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        notification = self.get_object()
        notification.read = True
        notification.save()
        return reverse("core:notification_list")


class NotificationMarkAllAsReadView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        Notification.objects.filter(user=self.request.user).update(read=True)
        return reverse("core:notification_list")
