from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.base import TemplateResponseMixin
from guardian.shortcuts import get_objects_for_user

from ephios.extra.mixins import CustomPermissionRequiredMixin


class EventBulkDeleteView(CustomPermissionRequiredMixin, TemplateResponseMixin, View):
    permission_required = "core.delete_event"
    template_name = "core/event_bulk_delete.html"

    def get(self, request, *args, **kwargs):
        events = get_objects_for_user(request.user, "core.change_event").filter(
            pk__in=request.GET.getlist("bulk_action")
        )
        if not events:
            messages.info(request, _("No events were selected for deletion."))
            return redirect(reverse("core:event_list"))
        return self.render_to_response({"events": events})

    def post(self, request, *args, **kwargs):
        events = get_objects_for_user(request.user, "core.change_event").filter(
            pk__in=request.POST.getlist("bulk_action")
        )
        if not events:
            messages.info(request, _("No events were selected for deletion."))
            return redirect(reverse("core:event_list"))
        if request.POST.get("confirm"):
            events.delete()
            messages.info(request, _("The selected events have been deleted."))
            return redirect(reverse("core:event_list"))
        return self.render_to_response({"events": events})
