from oauth2_provider.models import get_application_model
from oauth2_provider.views import ApplicationList

from ephios.extra.mixins import StaffRequiredMixin


class AllUserApplicationList(StaffRequiredMixin, ApplicationList):
    def get_queryset(self):
        return get_application_model().objects.all()
