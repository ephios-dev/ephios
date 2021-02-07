from django.views import View
from django.views.generic.detail import SingleObjectMixin

from ephios.extra.permissions import CustomPermissionRequiredMixin
from ephios.user_management.models import Shift


class SignupMethodViewMixin(SingleObjectMixin):
    model = Shift

    def dispatch(self, request, *args, **kwargs):
        return self.get_object().signup_method.signup_view(request, *args, **kwargs)


class ShiftSignupView(CustomPermissionRequiredMixin, SignupMethodViewMixin, View):
    permission_required = "user_management.view_event"

    def get_permission_object(self):
        return self.get_object().event
