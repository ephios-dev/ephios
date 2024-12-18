from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin

from ephios.core.consequences import ConsequenceError, editable_consequences


class ConsequenceUpdateView(LoginRequiredMixin, SingleObjectMixin, View):
    def get_queryset(self):
        return editable_consequences(self.request.user)

    def post(self, request, *args, **kwargs):
        consequence = self.get_object()
        fail_reason = None
        if request.POST["action"] == "deny":
            consequence.deny(request.user)
        elif request.POST["action"] == "confirm":
            try:
                consequence.confirm(request.user)
            except ConsequenceError as e:
                fail_reason = str(e)
        return JsonResponse(
            {
                "state": consequence.state,
                "fail_reason": fail_reason,
            }
        )
