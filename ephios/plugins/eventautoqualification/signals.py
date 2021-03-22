from django.dispatch import receiver

from ephios.core.signals import event_forms, periodic_signal
from ephios.plugins.eventautoqualification.consequences import create_qualification_consequences
from ephios.plugins.eventautoqualification.forms import EventAutoQualificationForm


@receiver(
    event_forms,
    dispatch_uid="ephios.plugins.eventautoqualification.signals.configuration_form",
)
def configuration_form(sender, event, request, **kwargs):
    if not request.user.has_perm("core:change_user"):
        return []

    return [EventAutoQualificationForm(request.POST or None, event=event)]


periodic_signal.connect(
    create_qualification_consequences,
    dispatch_uid="ephios.plugins.eventautoqualification.signals.create_qualification_consequences",
)
