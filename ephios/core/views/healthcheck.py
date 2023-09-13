from django.contrib.auth.models import Permission
from django.core import cache
from django.db import Error as DjangoDBError
from django.http import HttpResponse
from django.views import View


class HealthcheckView(View):
    def get(self, request, *args, **kwargs):
        # check db access
        try:
            Permission.objects.exists()
        except DjangoDBError:
            return HttpResponse("DB not available.", status=503)

        # check cache access
        cache.cache.set("_healthcheck", "1")
        if not cache.cache.get("_healthcheck") == "1":
            return HttpResponse("Cache not available.", status=503)

        return HttpResponse("OK", status=200)
