from django.core.exceptions import PermissionDenied
from django.views.generic import DetailView

from ephios.plugins.pages.models import Page


class PageView(DetailView):
    model = Page
    template_name = "pages/view_page.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = self.get_object()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated and not self.object.publicly_visible:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
