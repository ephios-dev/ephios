from django.views import View
from django.views.generic.detail import SingleObjectMixin

from ephios.core.models import Shift
from ephios.extra.permissions import CustomPermissionRequiredMixin


class SignupMethodViewMixin(SingleObjectMixin):
    model = Shift

    def dispatch(self, request, *args, **kwargs):
        return self.get_object().signup_method.signup_view(request, *args, **kwargs)


class ShiftSignupView(CustomPermissionRequiredMixin, SignupMethodViewMixin, View):
    permission_required = "core.view_event"

    def get_permission_object(self):
        return self.get_object().event
