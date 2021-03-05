from django.views import View
from django.views.generic.detail import SingleObjectMixin

from ephios.core.models import Shift
from ephios.extra.mixins import CustomPermissionRequiredMixin


class BaseSignupView(SingleObjectMixin, View):
    model = Shift

    def dispatch(self, request, *args, **kwargs):
        return self.get_object().signup_method.signup_view(request, *args, **kwargs)


class LocalUserSignupView(CustomPermissionRequiredMixin, BaseSignupView):
    permission_required = "core.view_event"

    def get_permission_object(self):
        return self.get_object().event
