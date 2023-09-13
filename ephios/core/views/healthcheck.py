from django.contrib.auth.models import Permission
from django.core import cache
from django.db import Error as DjangoDBError
from django.http import HttpResponse
from django.utils.formats import date_format
from django.views import View

from ephios.core.dynamic_preferences_registry import LastRunPeriodicCall


class HealthcheckView(View):
    def get(self, request, *args, **kwargs):
        messages = []
        errors = []
        # check db access
        try:
            Permission.objects.exists()
            messages.append("DB OK")
        except DjangoDBError:
            errors.append("DB not available")

        # check cache access
        cache.cache.set("_healthcheck", "1")
        if not cache.cache.get("_healthcheck") == "1":
            errors.append("Cache not available")
        else:
            messages.append("Cache OK")

        # check cronjob
        if LastRunPeriodicCall.is_stuck():
            if last_call := LastRunPeriodicCall.get_last_call():
                errors.append(
                    f"Cronjob stuck, last run {date_format(last_call,format='SHORT_DATETIME_FORMAT')}"
                )
            else:
                errors.append("Cronjob stuck, no last run")
        else:
            messages.append("Cronjob OK")

        if errors:
            return HttpResponse(
                "<br/>".join(errors) + "<br/><br/>" + "<br/>".join(messages), status=503
            )

        return HttpResponse("<br/>".join(messages), status=200)
