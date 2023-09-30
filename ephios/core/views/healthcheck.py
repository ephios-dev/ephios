from django.http import HttpResponse
from django.views import View

from ephios.core.services.health.healthchecks import HealthCheckStatus, run_healthchecks


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        okays = []
        not_okays = []

        for check, status, message in run_healthchecks():
            text = f"{check.name}: {message}"
            if status in {
                HealthCheckStatus.OK,
                HealthCheckStatus.WARNING,
                HealthCheckStatus.UNKNOWN,
            }:
                okays.append(text)
            else:
                not_okays.append(text)

        status = 200
        message = ""
        if not_okays:
            status = 503
            message += "NOT OK<br/><br/>" + "<br/>".join(not_okays) + "<br/><br/>"
        if okays:
            message += "OK<br/><br/>" + "<br/>".join(okays) + "<br/><br/>"
        return HttpResponse(message, status=status)
