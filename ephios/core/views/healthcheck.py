from django.http import HttpResponse
from django.views import View

from ephios.core.services.health.healthchecks import HealthCheckStatus, run_healthchecks


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        messages = []
        errors = []

        for check, status, message in run_healthchecks():
            text = f"{check.name}: {message}"
            if status == HealthCheckStatus.OK:
                messages.append(text)
            else:
                errors.append(text)

        if errors:
            return HttpResponse(
                "<br/>".join(errors) + "<br/><br/>" + "<br/>".join(messages), status=503
            )

        return HttpResponse("<br/>".join(messages), status=200)
