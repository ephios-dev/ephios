from django.dispatch import receiver

from ephios.core.signals import event_forms, participation_finished
from ephios.plugins.eventautoqualification.consequences import create_qualification_consequence
from ephios.plugins.eventautoqualification.forms import EventAutoQualificationForm


@receiver(
    event_forms,
    dispatch_uid="ephios.plugins.eventautoqualification.signals.configuration_form",
)
def configuration_form(sender, event, request, **kwargs):
    return [
        EventAutoQualificationForm(
            request.POST or None,
            event=event,
            edit_permission=request.user.has_perm("core.change_userprofile"),
        )
    ]


participation_finished.connect(
    create_qualification_consequence,
    dispatch_uid="ephios.plugins.eventautoqualification.signals.create_qualification_consequence",
)
