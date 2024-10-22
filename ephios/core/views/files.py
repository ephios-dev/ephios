from django.core.cache import cache
from django.http import Http404
from django.views import View

from ephios.extra.mixins import MediaViewMixin
from ephios.extra.utils import accelerated_media_response


class FileTicketView(MediaViewMixin, View):
    def get(self, request, *args, **kwargs):
        file = cache.get(self.kwargs["ticket"])
        if file is None:
            raise Http404()
        return accelerated_media_response(file)
