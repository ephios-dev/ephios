from django.contrib.auth.views import redirect_to_login
from django.views.generic import DetailView, ListView

from ephios.core.views.settings import SettingsViewMixin
from ephios.extra.mixins import StaffRequiredMixin
from ephios.plugins.pages.models import Page


class PageListView(StaffRequiredMixin, SettingsViewMixin, ListView):
    model = Page


class PageView(DetailView):
    model = Page

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = self.get_object()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated and not self.object.publicly_visible:
            return redirect_to_login(self.request.get_full_path())
        return super().dispatch(request, *args, **kwargs)
