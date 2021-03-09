from django.views import View
from django.views.generic.detail import SingleObjectMixin

from ephios.core.models import Shift
from ephios.core.signup import get_nonlocal_participant_from_session
from ephios.extra.mixins import CustomPermissionRequiredMixin


def request_to_participant(request):
    if request.user.is_authenticated:
        return request.user.as_participant()
    return get_nonlocal_participant_from_session(request)


class BaseShiftActionView(SingleObjectMixin, View):
    model = Shift

    def dispatch(self, request, *args, **kwargs):
        return self.get_object().signup_method.signup_view(
            request, *args, **{**kwargs, "participant": self.get_participant()}
        )

    def get_participant(self):
        raise NotImplementedError


class LocalUserShiftActionView(CustomPermissionRequiredMixin, BaseShiftActionView):
    permission_required = "core.view_event"

    def get_permission_object(self):
        return self.get_object().event

    def get_participant(self):
        return self.request.user.as_participant()
