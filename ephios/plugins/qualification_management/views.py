from django.views.generic import ListView

from ephios.core.models import Qualification
from ephios.core.views.settings import SettingsViewMixin
from ephios.extra.mixins import StaffRequiredMixin


# Templates in this plugin are under core/, because Qualification is a core model.
class QualificationListView(StaffRequiredMixin, SettingsViewMixin, ListView):
    model = Qualification
