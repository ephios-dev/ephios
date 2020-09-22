from django.core.handlers.wsgi import WSGIRequest
from django.views.generic import DetailView

from ephios.plugins.pages.models import Page

from django.core.exceptions import PermissionDenied


class PageView(DetailView):
    model = Page
    accept_global_perms = True
    template_name = "pages/view_page.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated and not self.object.publicly_visible:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
